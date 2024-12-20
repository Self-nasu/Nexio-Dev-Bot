import discord
from discord.ext import commands
from datetime import datetime
from firebase_admin import credentials, firestore, initialize_app, get_app

# Initialize Firebase
try:
    app = get_app("task_app")
except ValueError:
    cred = credentials.Certificate(r"G:\Discord Bots\NexioDevBot\nexio-discord-firebase-adminsdk-69kfk-4637335efd.json")
    app = initialize_app(cred, name="task_app")

db = firestore.client(app)
tasks_ref = db.collection("tasks")
FIXED_CHANNEL_ID = 1319197182682726452  # Replace with your channel ID

class TaskManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_next_task_id(self):
        tasks = tasks_ref.order_by("task_id").stream()
        max_id = 0
        for task in tasks:
            task_id = task.to_dict().get("task_id", "")
            if task_id.startswith("TASK"):
                max_id = max(max_id, int(task_id[4:]))
        return f"TASK{max_id + 1}"

    async def update_task_embed(self, task_id, embed):
        task = tasks_ref.document(task_id).get()
        if task.exists:
            task_data = task.to_dict()
            channel = self.bot.get_channel(int(task_data["channel_id"]))
            if channel:
                try:
                    message = await channel.fetch_message(task_data["message_id"])
                    await message.edit(embed=embed)
                    return message
                except discord.NotFound:
                    return None
        return None

    @discord.app_commands.command(
        name="addtask",
        description="Add a new task. Due date format: YYYY-MM-DD. Optionally provide a channel."
    )
    async def addtask(self, interaction: discord.Interaction, name: str, description: str, due_date: str, channel: discord.TextChannel = None):
        try:
            due_date_parsed = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD.", ephemeral=True)
            return

        task_id = self.get_next_task_id()
        channel = channel or interaction.channel

        embed = discord.Embed(title="New Task Added", color=discord.Color.red())
        embed.add_field(name="Task ID", value=task_id, inline=False)
        embed.add_field(name="Task", value=name, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Due Date", value=due_date_parsed.strftime("%B %d, %Y"), inline=False)
        embed.add_field(name="Created By", value=interaction.user.name, inline=False)
        embed.set_footer(text="Use /taskdone <Task ID> to mark this task as complete.")

        message = await channel.send(f"@everyone new task is added", embed=embed)

        tasks_ref.document(task_id).set({
            "task_id": task_id,
            "name": name,
            "description": description,
            "due_date": due_date_parsed.isoformat(),
            "created_at": datetime.now().isoformat(),
            "channel_id": str(channel.id),
            "message_id": message.id,
            "completed": False
        })

        await interaction.response.send_message(f"Task '{name}' added successfully with Task ID `{task_id}`!", ephemeral=True)

    @discord.app_commands.command(
        name="taskdone",
        description="Mark a task as completed. Provide Task ID."
    )
    async def taskdone(self, interaction: discord.Interaction, task_id: str):
        task_doc = tasks_ref.document(task_id).get()
        if task_doc.exists:
            task = task_doc.to_dict()
            embed = discord.Embed(title="Task Completed ✅", color=discord.Color.green())
            embed.add_field(name="Task ID", value=task_id, inline=False)
            embed.add_field(name="Task", value=task["name"], inline=False)
            embed.add_field(name="Description", value=f"~~{task['description']}~~", inline=False)
            embed.add_field(name="Due Date", value=datetime.fromisoformat(task["due_date"]).strftime("%B %d, %Y"), inline=False)
            embed.add_field(name="Completed On", value=datetime.now().strftime("%B %d, %Y, %I:%M %p"), inline=False)

            if await self.update_task_embed(task_id, embed):
                tasks_ref.document(task_id).update({"completed": True})
                await interaction.response.send_message(f"Task with ID `{task_id}` marked as complete!", ephemeral=True)
            else:
                await interaction.response.send_message("Could not find the original task message.", ephemeral=True)
        else:
            await interaction.response.send_message("Task not found. Please check the Task ID.", ephemeral=True)

    @discord.app_commands.command(
        name="deletetask",
        description="Delete a task by ID. Provide Task ID."
    )
    async def deletetask(self, interaction: discord.Interaction, task_id: str):
        task_doc = tasks_ref.document(task_id).get()
        if task_doc.exists:
            task = task_doc.to_dict()
            try:
                channel = self.bot.get_channel(int(task["channel_id"]))
                message = await channel.fetch_message(task["message_id"])
                await message.delete()
                tasks_ref.document(task_id).delete()
                await interaction.response.send_message(f"Task with ID `{task_id}` has been deleted.", ephemeral=True)
            except discord.NotFound:
                await interaction.response.send_message("The task message could not be found.", ephemeral=True)
        else:
            await interaction.response.send_message("Task not found. Please check the Task ID.", ephemeral=True)

    @discord.app_commands.command(
        name="tasklist",
        description="View all active tasks."
    )
    async def tasklist(self, interaction: discord.Interaction):
        tasks = tasks_ref.where("completed", "==", False).stream()
        embed = discord.Embed(title="Active Tasks", color=discord.Color.blue())
        found = False
        for task in tasks:
            task_data = task.to_dict()
            embed.add_field(
                name=f"Task ID {task_data['task_id']}: {task_data['name']}",
                value=f"Due: {datetime.fromisoformat(task_data['due_date']).strftime('%B %d, %Y')}\nDescription: {task_data['description']}",
                inline=False
            )
            found = True

        if not found:
            await interaction.response.send_message("No active tasks found.", ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(
        name="alltasks",
        description="View all tasks (completed tasks will be struck through)."
    )
    async def alltasks(self, interaction: discord.Interaction):
        tasks = tasks_ref.stream()
        embed = discord.Embed(title="All Tasks", color=discord.Color.blue())
        found = False
        for task in tasks:
            task_data = task.to_dict()
            description = f"~~{task_data['description']}~~" if task_data["completed"] else task_data["description"]
            embed.add_field(
                name=f"Task ID {task_data['task_id']}: {task_data['name']}",
                value=f"Due: {datetime.fromisoformat(task_data['due_date']).strftime('%B %d, %Y')}\nDescription: {description}",
                inline=False
            )
            found = True

        if not found:
            await interaction.response.send_message("No tasks found.", ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(
        name="monthlytask",
        description="Add a new monthly task. This is only for Core Team members."
    )
    async def monthlytask(self, interaction: discord.Interaction, name: str, description: str, due_date: str):
        core_team_role = discord.utils.get(interaction.user.roles, name="Core Team")
        if not core_team_role:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        try:
            due_date_parsed = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD.", ephemeral=True)
            return

        task_id = self.get_next_task_id()
        fixed_channel = self.bot.get_channel(FIXED_CHANNEL_ID)

        if not fixed_channel:
            await interaction.response.send_message("The fixed channel is not available. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title="Monthly Task Added", color=discord.Color.gold())
        embed.add_field(name="Task ID", value=task_id, inline=False)
        embed.add_field(name="Task", value=name, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Due Date", value=due_date_parsed.strftime("%B %d, %Y"), inline=False)
        embed.add_field(name="Assigned By", value=interaction.user.name, inline=False)
        embed.set_footer(text="Monthly tasks for Core Team members.")

        message = await fixed_channel.send(f"@everyone new monthly task is added", embed=embed)

        tasks_ref.document(task_id).set({
            "task_id": task_id,
            "name": name,
            "description": description,
            "due_date": due_date_parsed.isoformat(),
            "created_at": datetime.now().isoformat(),
            "channel_id": str(fixed_channel.id),
            "message_id": message.id,
            "completed": False
        })

        await interaction.response.send_message(f"Monthly task '{name}' added successfully with Task ID `{task_id}`!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskManagerCog(bot))
