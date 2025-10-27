#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Workout CLI: A command-line tool to track your daily workouts.
"""

import typer
from rich.console import Console
from rich.table import Table
import datetime
from pathlib import Path
import re
from typing import List, Optional

# --- Configuration ---
DATA_FILE = Path("workout_log.md")
console = Console()

# --- Main Application ---
app = typer.Typer(
    help="A CLI tool to log your workouts in a single Markdown file.",
    rich_markup_mode="markdown"
)

# --- Helper Functions ---
def get_actions() -> List[str]:
    """Parses and returns the list of available actions from the data file."""
    content = DATA_FILE.read_text(encoding="utf-8")
    actions_match = re.search(r"## 可用动作\n(.+?)\n##", content, re.DOTALL)
    if actions_match:
        actions_text = actions_match.group(1)
        return [line.strip()[2:] for line in actions_text.strip().split('\n') if line.strip().startswith('- ')]
    return []

def get_today_date() -> str:
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.datetime.now().strftime("%Y-%m-%d")

def initialize_storage():
    """Creates the markdown data file if it doesn't exist with a default structure."""
    if not DATA_FILE.exists():
        console.print(f"Data file '{DATA_FILE}' not found. Creating a new one.")
        content = """# 我的训练日志

## 可用动作
- 深蹲 (Squat)
- 卧推 (Bench Press)
- 硬拉 (Deadlift)

## 训练目标
- 深蹲: 120 kg
- 卧推: 100 kg

"""
        DATA_FILE.write_text(content, encoding="utf-8")

# --- Typer Commands ---

@app.callback()
def main():
    """
    Initialize the data file before running any command.
    """
    initialize_storage()

# --- Action Subcommand ---
action_app = typer.Typer(help="管理可用动作 (Manage available actions).")
app.add_typer(action_app, name="action")

@action_app.command("show", help="显示所有可用动作 (Show all available actions).")
def action_show():
    """Displays all available workout actions in a table."""
    actions = get_actions()
    if not actions:
        console.print("[yellow]动作列表为空，请使用 'action add' 添加一个。[/yellow]")
        return

    table = Table("可用动作 (Available Actions)")
    for action in actions:
        table.add_row(action)
    console.print(table)

@action_app.command("add", help="添加一个新动作 (Add a new action).")
def action_add(
    name: str = typer.Argument(..., help="要添加的动作名称 (The name of the action to add).")
):
    """Adds a new workout action to the list in the markdown file."""
    actions = get_actions()
    if name in actions:
        console.print(f"[bold red]错误: 动作 '{name}' 已存在。[/bold red]")
        raise typer.Exit(code=1)

    content = DATA_FILE.read_text(encoding="utf-8")
    # Use a regex to find the actions section and insert the new action
    new_content, count = re.subn(
        r"(## 可用动作\n)",
        rf"\1- {name}\n",
        content,
        count=1 # ensure we only substitute once
    )

    if count > 0:
        DATA_FILE.write_text(new_content, encoding="utf-8")
        console.print(f"[bold green]成功添加动作: '{name}'[/bold green]")
    else:
        console.print("[bold red]错误: 未找到 '## 可用动作' 标题。文件可能已损坏。[/bold red]")
        raise typer.Exit(code=1)

@app.command(help="记录一次训练 (Record a workout session).")
def record(
    action_name: str = typer.Argument(..., help="动作名称 (Name of the action)."),
    reps: int = typer.Argument(..., help="每组次数 (Repetitions per set)."),
    kg: float = typer.Argument(..., help="重量 (Weight in KG)."),
    sets: int = typer.Option(1, "--sets", "-s", help="组数 (Number of sets)."),
):
    """Records a single workout set to the markdown file."""
    # 1. Validate action
    actions = get_actions()
    # Find the full action name (case-insensitive partial match)
    matched_action = None
    for action in actions:
        if action_name.lower() in action.lower():
            matched_action = action
            break

    if not matched_action:
        console.print(f"[bold red]错误: 动作 '{action_name}' 未在可用列表中找到。[/bold red]")
        console.print("请先使用 `action add` 添加，或检查拼写。")
        raise typer.Exit(code=1)

    # 2. Calculate volume
    volume = sets * reps * kg

    # 3. Find or create today's log section
    today_str = get_today_date()
    date_header = f"## {today_str}"
    table_header = "| 动作 (Action) | 组数 (Sets) | 次数 (Rps) | 重量 (KG) | 训练量 (Volume) |\n|---------------|-------------|------------|-----------|-----------------|"
    new_record_row = f"| {matched_action} | {sets} | {reps} | {kg} | {volume} |"

    content = DATA_FILE.read_text(encoding="utf-8")
    
    # Check for Personal Record (PR) before modifying the file
    all_records_for_action = re.findall(
        rf"\|\s*{re.escape(matched_action)}\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)\s*\|",
        content
    )
    max_weight_before = 0.0
    if all_records_for_action:
        max_weight_before = max(float(w) for w in all_records_for_action)

    is_pr = kg > max_weight_before

    # Append the record
    if date_header in content:
        # Append to existing date by simply adding the row to the end of the file
        with DATA_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n{new_record_row}")
    else:
        # Add new date section at the end of the file
        with DATA_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n\n{date_header}\n{table_header}\n{new_record_row}")

    # 4. Display confirmation
    console.print(f"[green]记录成功: {sets}x{reps} {matched_action} @ {kg}kg. 训练量: {volume}kg.[/green]")

    # 5. Celebrate PR
    if is_pr:
        console.print(f"[bold yellow]🎉 恭喜！你创造了新的个人纪录 (PR) in {matched_action} at {kg}kg! (之前是 {max_weight_before}kg) 🔥[/bold yellow]")

@app.command(help="显示所有历史训练记录 (Show all historical workout logs).")
def history():
    """Parses and displays all workout records from the markdown file by reading it line by line."""
    lines = DATA_FILE.read_text(encoding="utf-8").splitlines()

    table = Table(title="训练历史记录")
    headers = ["日期 (Date)", "动作 (Action)", "组数 (Sets)", "次数 (Reps)", "重量 (KG)", "训练量 (Volume)"]
    for header in headers:
        table.add_column(header, no_wrap=True)

    current_date = None
    found_records = False
    for line in lines:
        # Find date headers like '## 2025-10-27'
        date_match = re.match(r"## (\d{4}-\d{2}-\d{2})", line.strip())
        if date_match:
            current_date = date_match.group(1)
            continue

        # Process only valid data rows within a date section
        if current_date and line.strip().startswith("|") and "---" not in line:
            # Split by '|' and clean up parts
            parts = [p.strip() for p in line.strip().split('|')]
            # Expect ['', 'action', 'sets', 'reps', 'kg', 'volume', '']
            if len(parts) == 7:
                _, action, sets, reps, kg, volume, _ = parts
                # Ensure we don't add empty rows from table headers
                if action and "Action" not in action:
                    table.add_row(current_date, action, sets, reps, kg, volume)
                    found_records = True

    if not found_records:
        console.print("[yellow]还没有任何训练记录。[/yellow]")
        return

    console.print(table)


if __name__ == "__main__":
    app()
