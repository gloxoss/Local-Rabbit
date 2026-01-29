#!/usr/bin/env python3
"""
Local CodeRabbit - Multi-Project Manager
Manage multiple projects with aggregated stats and project switching.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """Project configuration"""
    id: str
    name: str
    path: str
    enabled: bool
    last_scan: Optional[str]
    issues: dict  # {critical, warning, suggestion}
    health_score: int
    team_members: list[str]


@dataclass
class ProjectGroup:
    """Group of related projects"""
    id: str
    name: str
    project_ids: list[str]


class ProjectManager:
    """Manages multiple projects"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".coderabbit" / "projects.json"
        self.projects: dict[str, Project] = {}
        self.groups: dict[str, ProjectGroup] = {}
        self._load_config()
    
    def _load_config(self):
        """Load project configuration"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                
                for p in data.get("projects", []):
                    project = Project(
                        id=p["id"],
                        name=p["name"],
                        path=p["path"],
                        enabled=p.get("enabled", True),
                        last_scan=p.get("last_scan"),
                        issues=p.get("issues", {"critical": 0, "warning": 0, "suggestion": 0}),
                        health_score=p.get("health_score", 0),
                        team_members=p.get("team_members", [])
                    )
                    self.projects[p["id"]] = project
                
                for g in data.get("groups", []):
                    group = ProjectGroup(
                        id=g["id"],
                        name=g["name"],
                        project_ids=g.get("project_ids", [])
                    )
                    self.groups[g["id"]] = group
                    
            except Exception as e:
                print(f"Warning: Could not load projects config: {e}")
    
    def _save_config(self):
        """Save project configuration"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "path": p.path,
                    "enabled": p.enabled,
                    "last_scan": p.last_scan,
                    "issues": p.issues,
                    "health_score": p.health_score,
                    "team_members": p.team_members
                }
                for p in self.projects.values()
            ],
            "groups": [
                {
                    "id": g.id,
                    "name": g.name,
                    "project_ids": g.project_ids
                }
                for g in self.groups.values()
            ]
        }
        
        self.config_path.write_text(json.dumps(data, indent=2))
    
    def add_project(self, name: str, path: str) -> Project:
        """Add a new project"""
        project_id = name.lower().replace(" ", "-")
        counter = 1
        while project_id in self.projects:
            project_id = f"{name.lower().replace(' ', '-')}-{counter}"
            counter += 1
        
        project = Project(
            id=project_id,
            name=name,
            path=str(Path(path).resolve()),
            enabled=True,
            last_scan=None,
            issues={"critical": 0, "warning": 0, "suggestion": 0},
            health_score=0,
            team_members=[]
        )
        
        self.projects[project_id] = project
        self._save_config()
        
        return project
    
    def remove_project(self, project_id: str) -> bool:
        """Remove a project"""
        if project_id in self.projects:
            del self.projects[project_id]
            self._save_config()
            return True
        return False
    
    def update_project_stats(self, project_id: str, issues: dict, health_score: int):
        """Update project statistics"""
        if project_id in self.projects:
            project = self.projects[project_id]
            project.issues = issues
            project.health_score = health_score
            project.last_scan = datetime.now().isoformat()
            self._save_config()
    
    def get_aggregate_stats(self) -> dict:
        """Get aggregated stats across all projects"""
        total_critical = 0
        total_warning = 0
        total_suggestion = 0
        total_score = 0
        active_projects = 0
        
        for project in self.projects.values():
            if project.enabled:
                total_critical += project.issues.get("critical", 0)
                total_warning += project.issues.get("warning", 0)
                total_suggestion += project.issues.get("suggestion", 0)
                total_score += project.health_score
                active_projects += 1
        
        avg_score = total_score / active_projects if active_projects > 0 else 0
        
        return {
            "projects": len(self.projects),
            "active_projects": active_projects,
            "issues": {
                "critical": total_critical,
                "warning": total_warning,
                "suggestion": total_suggestion,
                "total": total_critical + total_warning + total_suggestion
            },
            "average_health_score": round(avg_score, 1)
        }
    
    def get_projects_by_status(self) -> dict:
        """Get projects grouped by status"""
        healthy = []  # 0 critical, health > 80
        attention = []  # Some warnings or health < 80
        critical_proj = []  # Has critical issues
        
        for project in self.projects.values():
            if not project.enabled:
                continue
            
            if project.issues.get("critical", 0) > 0:
                critical_proj.append(project)
            elif project.health_score < 80 or project.issues.get("warning", 0) > 5:
                attention.append(project)
            else:
                healthy.append(project)
        
        return {
            "healthy": healthy,
            "needs_attention": attention,
            "critical": critical_proj
        }
    
    def create_group(self, name: str, project_ids: list[str] = None) -> ProjectGroup:
        """Create a project group"""
        group_id = name.lower().replace(" ", "-")
        
        group = ProjectGroup(
            id=group_id,
            name=name,
            project_ids=project_ids or []
        )
        
        self.groups[group_id] = group
        self._save_config()
        
        return group
    
    def list_projects(self) -> list[Project]:
        """List all projects"""
        return list(self.projects.values())
    
    def generate_dashboard_json(self) -> str:
        """Generate JSON for multi-project dashboard"""
        aggregate = self.get_aggregate_stats()
        by_status = self.get_projects_by_status()
        
        return json.dumps({
            "generatedAt": datetime.now().isoformat(),
            "aggregate": aggregate,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "path": p.path,
                    "enabled": p.enabled,
                    "lastScan": p.last_scan,
                    "issues": p.issues,
                    "healthScore": p.health_score,
                    "status": "critical" if p.issues.get("critical", 0) > 0 
                             else "warning" if p.issues.get("warning", 0) > 3 
                             else "healthy"
                }
                for p in self.projects.values()
            ],
            "statusCounts": {
                "healthy": len(by_status["healthy"]),
                "needsAttention": len(by_status["needs_attention"]),
                "critical": len(by_status["critical"])
            }
        }, indent=2)


def print_projects_table(manager: ProjectManager):
    """Print projects as formatted table"""
    projects = manager.list_projects()
    
    print("=" * 70)
    print(f"{'PROJECT':<25} {'STATUS':<12} {'ISSUES':<15} {'HEALTH':<8}")
    print("=" * 70)
    
    for p in projects:
        status = "●" if p.enabled else "○"
        status_text = "Critical" if p.issues.get("critical", 0) > 0 else "Warning" if p.issues.get("warning", 0) > 3 else "Healthy"
        
        status_color = "\033[31m" if status_text == "Critical" else "\033[33m" if status_text == "Warning" else "\033[32m"
        reset = "\033[0m"
        
        issues = f"{p.issues.get('critical', 0)}C/{p.issues.get('warning', 0)}W"
        health = f"{p.health_score}%"
        
        print(f"{status} {p.name:<23} {status_color}{status_text:<12}{reset} {issues:<15} {health:<8}")
    
    print("=" * 70)
    
    # Aggregate
    agg = manager.get_aggregate_stats()
    print(f"\nTotal: {agg['projects']} projects, {agg['issues']['total']} issues, avg health: {agg['average_health_score']}%")


if __name__ == "__main__":
    import sys
    
    manager = ProjectManager()
    
    if len(sys.argv) < 2:
        print("Usage: python multi_project.py <command> [args]")
        print("\nCommands:")
        print("  list                    - List all projects")
        print("  add <name> <path>       - Add a new project")
        print("  remove <id>             - Remove a project")
        print("  stats                   - Show aggregate stats")
        print("  json                    - Output dashboard JSON")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        print_projects_table(manager)
    
    elif command == "add" and len(sys.argv) >= 4:
        name = sys.argv[2]
        path = sys.argv[3]
        project = manager.add_project(name, path)
        print(f"Added project: {project.name} ({project.id})")
    
    elif command == "remove" and len(sys.argv) >= 3:
        project_id = sys.argv[2]
        if manager.remove_project(project_id):
            print(f"Removed project: {project_id}")
        else:
            print(f"Project not found: {project_id}")
    
    elif command == "stats":
        agg = manager.get_aggregate_stats()
        print(f"Projects: {agg['projects']} ({agg['active_projects']} active)")
        print(f"Issues: {agg['issues']['critical']} critical, {agg['issues']['warning']} warnings")
        print(f"Average Health: {agg['average_health_score']}%")
    
    elif command == "json":
        print(manager.generate_dashboard_json())
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
