"""Skills management commands."""
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


SKILL_TEMPLATE = """---
name: {skill_name}
description: Brief description of what this skill does
---

# {skill_name}

## Purpose
Explain what this skill is for and when to use it.

## Instructions
Provide step-by-step instructions for the agent.

1. First step
2. Second step
3. ...

## Examples
Show examples of how to use this skill.

## Notes
Any additional context or warnings.
"""


@app.command("list")
def list_skills(
    working_dir: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Working directory",
    ),
    agent_name: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent name",
    ),
    project_wide: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="List project-wide skills instead of agent-specific",
    ),
):
    """List available skills."""
    if project_wide:
        skills_dir = working_dir / ".ldv-agents" / "skills"
        location = "Project-local"
    else:
        skills_dir = Path.home() / ".ldv-agents" / agent_name / "skills"
        location = f"Agent '{agent_name}'"
    
    if not skills_dir.exists():
        console.print(f"[yellow]No skills directory found at {skills_dir}[/yellow]")
        return
    
    # Find all SKILL.md files
    skill_files = list(skills_dir.rglob("SKILL.md"))
    
    if not skill_files:
        console.print(f"[yellow]No skills found in {skills_dir}[/yellow]")
        return
    
    table = Table(title=f"{location} Skills")
    table.add_column("Skill Name", style="cyan")
    table.add_column("Path", style="dim")
    
    for skill_file in sorted(skill_files):
        skill_name = skill_file.parent.name
        rel_path = skill_file.relative_to(skills_dir)
        table.add_row(skill_name, str(rel_path.parent))
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(skill_files)} skill(s)[/dim]")


@app.command("create")
def create_skill(
    name: str = typer.Argument(..., help="Skill name"),
    working_dir: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Working directory",
    ),
    agent_name: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent name",
    ),
    project_wide: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Create as project-wide skill instead of agent-specific",
    ),
):
    """Create a new skill with template."""
    if project_wide:
        skills_dir = working_dir / ".ldv-agents" / "skills"
        location = "project-local"
    else:
        skills_dir = Path.home() / ".ldv-agents" / agent_name / "skills"
        location = f"agent '{agent_name}'"
    
    skill_dir = skills_dir / name
    skill_file = skill_dir / "SKILL.md"
    
    if skill_file.exists():
        console.print(f"[red]Skill '{name}' already exists at {skill_file}[/red]")
        raise typer.Exit(1)
    
    # Create directory
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Write template
    content = SKILL_TEMPLATE.format(skill_name=name)
    skill_file.write_text(content)
    
    console.print(f"[green]✓[/green] Created {location} skill: {skill_file}")
    console.print(f"\n[dim]Edit {skill_file} to customize the skill[/dim]")


@app.command("delete")
def delete_skill(
    name: str = typer.Argument(..., help="Skill name to delete"),
    working_dir: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Working directory",
    ),
    agent_name: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent name",
    ),
    project_wide: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Delete from project-wide skills instead of agent-specific",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
):
    """Delete a skill."""
    if project_wide:
        skills_dir = working_dir / ".ldv-agents" / "skills"
    else:
        skills_dir = Path.home() / ".ldv-agents" / agent_name / "skills"
    
    skill_dir = skills_dir / name
    
    if not skill_dir.exists():
        console.print(f"[red]Skill '{name}' not found at {skill_dir}[/red]")
        raise typer.Exit(1)
    
    if not force:
        confirm = typer.confirm(f"Delete skill '{name}' and all its contents?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Delete the directory
    import shutil
    shutil.rmtree(skill_dir)
    
    console.print(f"[green]✓[/green] Deleted skill: {name}")


@app.command("info")
def skill_info(
    name: str = typer.Argument(..., help="Skill name"),
    working_dir: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Working directory",
    ),
    agent_name: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent name",
    ),
    project_wide: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Show project-wide skill instead of agent-specific",
    ),
):
    """Show detailed information about a skill."""
    if project_wide:
        skills_dir = working_dir / ".ldv-agents" / "skills"
    else:
        skills_dir = Path.home() / ".ldv-agents" / agent_name / "skills"
    
    skill_file = skills_dir / name / "SKILL.md"
    
    if not skill_file.exists():
        console.print(f"[red]Skill '{name}' not found at {skill_file}[/red]")
        raise typer.Exit(1)
    
    content = skill_file.read_text()
    console.print(f"[bold cyan]{name}[/bold cyan]")
    console.print(f"[dim]Location: {skill_file}[/dim]\n")
    console.print(content)
