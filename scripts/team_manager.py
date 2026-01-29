#!/usr/bin/env python3
"""
Local CodeRabbit - Team Management
Manage team members, code ownership, and review assignments.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import fnmatch


@dataclass
class TeamMember:
    """Represents a team member"""
    id: str
    name: str
    email: Optional[str]
    github: Optional[str]
    role: str  # admin, developer, reviewer
    avatar_url: Optional[str]


@dataclass
class OwnershipRule:
    """Code ownership rule"""
    pattern: str  # Glob pattern like "frontend/*" or "*.py"
    owners: list[str]  # Team member IDs
    reviewers: list[str]  # Required reviewers
    auto_assign: bool


class TeamManager:
    """Manages team members and code ownership"""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path("team.json")
        self.members: dict[str, TeamMember] = {}
        self.ownership_rules: list[OwnershipRule] = []
        self._load_config()
    
    def _load_config(self):
        """Load team configuration"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                
                for m in data.get("members", []):
                    member = TeamMember(
                        id=m["id"],
                        name=m["name"],
                        email=m.get("email"),
                        github=m.get("github"),
                        role=m.get("role", "developer"),
                        avatar_url=m.get("avatar_url")
                    )
                    self.members[m["id"]] = member
                
                for r in data.get("ownership", []):
                    rule = OwnershipRule(
                        pattern=r["pattern"],
                        owners=r.get("owners", []),
                        reviewers=r.get("reviewers", []),
                        auto_assign=r.get("auto_assign", False)
                    )
                    self.ownership_rules.append(rule)
                    
            except Exception as e:
                print(f"Warning: Could not load team config: {e}")
    
    def _save_config(self):
        """Save team configuration"""
        data = {
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "github": m.github,
                    "role": m.role,
                    "avatar_url": m.avatar_url
                }
                for m in self.members.values()
            ],
            "ownership": [
                {
                    "pattern": r.pattern,
                    "owners": r.owners,
                    "reviewers": r.reviewers,
                    "auto_assign": r.auto_assign
                }
                for r in self.ownership_rules
            ]
        }
        
        self.config_path.write_text(json.dumps(data, indent=2))
    
    def add_member(self, name: str, email: str = None, github: str = None, role: str = "developer") -> TeamMember:
        """Add a new team member"""
        member_id = name.lower().replace(" ", "_")
        counter = 1
        while member_id in self.members:
            member_id = f"{name.lower().replace(' ', '_')}_{counter}"
            counter += 1
        
        member = TeamMember(
            id=member_id,
            name=name,
            email=email,
            github=github,
            role=role,
            avatar_url=None
        )
        
        self.members[member_id] = member
        self._save_config()
        
        return member
    
    def remove_member(self, member_id: str) -> bool:
        """Remove a team member"""
        if member_id in self.members:
            del self.members[member_id]
            self._save_config()
            return True
        return False
    
    def add_ownership_rule(self, pattern: str, owners: list[str], reviewers: list[str] = None, auto_assign: bool = False):
        """Add code ownership rule"""
        rule = OwnershipRule(
            pattern=pattern,
            owners=owners,
            reviewers=reviewers or [],
            auto_assign=auto_assign
        )
        self.ownership_rules.append(rule)
        self._save_config()
    
    def get_owners(self, file_path: str) -> list[TeamMember]:
        """Get owners for a file path"""
        owners = []
        
        for rule in self.ownership_rules:
            if fnmatch.fnmatch(file_path, rule.pattern) or fnmatch.fnmatch(file_path, f"*/{rule.pattern}"):
                for owner_id in rule.owners:
                    if owner_id in self.members:
                        owners.append(self.members[owner_id])
        
        return list({o.id: o for o in owners}.values())  # Deduplicate
    
    def get_reviewers(self, file_path: str) -> list[TeamMember]:
        """Get required reviewers for a file path"""
        reviewers = []
        
        for rule in self.ownership_rules:
            if fnmatch.fnmatch(file_path, rule.pattern) or fnmatch.fnmatch(file_path, f"*/{rule.pattern}"):
                for reviewer_id in rule.reviewers:
                    if reviewer_id in self.members:
                        reviewers.append(self.members[reviewer_id])
        
        return list({r.id: r for r in reviewers}.values())
    
    def assign_reviewers(self, files: list[str]) -> dict[str, list[TeamMember]]:
        """Automatically assign reviewers for files"""
        assignments = {}
        
        for file_path in files:
            owners = self.get_owners(file_path)
            reviewers = self.get_reviewers(file_path)
            
            # Combine owners and designated reviewers
            all_reviewers = list({r.id: r for r in owners + reviewers}.values())
            
            if all_reviewers:
                assignments[file_path] = all_reviewers
            else:
                # No specific owners, assign to admins
                admins = [m for m in self.members.values() if m.role == "admin"]
                if admins:
                    assignments[file_path] = admins
        
        return assignments
    
    def get_member_stats(self, reviews_dir: Path) -> dict[str, dict]:
        """Get stats for each team member"""
        history_dir = reviews_dir / "history"
        stats = {m.id: {"reviews": 0, "issues_found": 0} for m in self.members.values()}
        
        if not history_dir.exists():
            return stats
        
        for file in history_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                author = data.get("author", {}).get("name", "").lower().replace(" ", "_")
                
                if author in stats:
                    stats[author]["reviews"] += 1
                    issues = data.get("issues", {})
                    stats[author]["issues_found"] += (
                        len(issues.get("critical", [])) +
                        len(issues.get("warning", [])) +
                        len(issues.get("suggestion", []))
                    )
            except:
                continue
        
        return stats
    
    def generate_codeowners(self) -> str:
        """Generate CODEOWNERS file content"""
        lines = [
            "# CODEOWNERS",
            "# Generated by Local CodeRabbit",
            f"# Last updated: {datetime.now().isoformat()}",
            ""
        ]
        
        for rule in self.ownership_rules:
            github_handles = []
            for owner_id in rule.owners:
                if owner_id in self.members and self.members[owner_id].github:
                    github_handles.append(f"@{self.members[owner_id].github}")
            
            if github_handles:
                lines.append(f"{rule.pattern} {' '.join(github_handles)}")
        
        return "\n".join(lines)
    
    def list_members(self) -> list[TeamMember]:
        """List all team members"""
        return list(self.members.values())


def create_default_team_config():
    """Create a default team.json configuration"""
    return {
        "members": [
            {
                "id": "admin",
                "name": "Admin",
                "email": "admin@example.com",
                "github": "admin",
                "role": "admin"
            }
        ],
        "ownership": [
            {
                "pattern": "*.py",
                "owners": ["admin"],
                "reviewers": [],
                "auto_assign": True
            },
            {
                "pattern": "*.ts",
                "owners": ["admin"],
                "reviewers": [],
                "auto_assign": True
            }
        ]
    }


if __name__ == "__main__":
    import sys
    
    manager = TeamManager()
    
    if len(sys.argv) < 2:
        print("Usage: python team_manager.py <command> [args]")
        print("\nCommands:")
        print("  list                        - List all team members")
        print("  add <name> [email] [github] - Add a team member")
        print("  remove <id>                 - Remove a team member")
        print("  owners <file>               - Get owners for a file")
        print("  assign <file1> [file2] ...  - Assign reviewers to files")
        print("  codeowners                  - Generate CODEOWNERS file")
        print("  init                        - Create default team.json")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        members = manager.list_members()
        if not members:
            print("No team members configured. Run 'init' to create default config.")
        else:
            print(f"{'ID':<15} {'NAME':<20} {'ROLE':<12} {'GITHUB':<15}")
            print("=" * 62)
            for m in members:
                print(f"{m.id:<15} {m.name:<20} {m.role:<12} {m.github or '-':<15}")
    
    elif command == "add" and len(sys.argv) >= 3:
        name = sys.argv[2]
        email = sys.argv[3] if len(sys.argv) > 3 else None
        github = sys.argv[4] if len(sys.argv) > 4 else None
        member = manager.add_member(name, email, github)
        print(f"Added member: {member.name} ({member.id})")
    
    elif command == "remove" and len(sys.argv) >= 3:
        member_id = sys.argv[2]
        if manager.remove_member(member_id):
            print(f"Removed member: {member_id}")
        else:
            print(f"Member not found: {member_id}")
    
    elif command == "owners" and len(sys.argv) >= 3:
        file_path = sys.argv[2]
        owners = manager.get_owners(file_path)
        if owners:
            print(f"Owners for {file_path}:")
            for o in owners:
                print(f"  - {o.name} ({o.id})")
        else:
            print(f"No owners found for {file_path}")
    
    elif command == "assign" and len(sys.argv) >= 3:
        files = sys.argv[2:]
        assignments = manager.assign_reviewers(files)
        for file_path, reviewers in assignments.items():
            print(f"{file_path}:")
            for r in reviewers:
                print(f"  - {r.name}")
    
    elif command == "codeowners":
        print(manager.generate_codeowners())
    
    elif command == "init":
        if Path("team.json").exists():
            print("team.json already exists. Remove it first to reinitialize.")
        else:
            Path("team.json").write_text(json.dumps(create_default_team_config(), indent=2))
            print("Created team.json with default configuration")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
