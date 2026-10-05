import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class ProjectContextLoader:
    """Discovers, loads, and compiles project rules and skills before execution."""

    MANDATORY_GLOBAL_RULES = [
        {
            "id": "RULE_NO_VIETNAMESE_IN_CODE",
            "title": "No Vietnamese in Source Code",
            "content": (
                "Never write comments, annotations, or docstrings in Vietnamese inside code files "
                "(.cs, .py, .js, .ts, .cpp, .shader, etc.). Any necessary code comments must be written in English."
            ),
            "source": "Global Policy",
        },
        {
            "id": "RULE_MINIMAL_COMMENTS",
            "title": "Minimal & Essential Comments Only",
            "content": (
                "Do not write comments for obvious or trivial code. Only add comments for complex algorithms, "
                "critical formulas, or non-obvious edge cases. Prefer clean, self-explanatory code."
            ),
            "source": "Global Policy",
        },
    ]

    UNITY_CONSTRAINTS = [
        {
            "id": "RULE_UNITY_BEST_PRACTICES",
            "title": "Unity C# Code Standards",
            "content": (
                "1. Follow standard Unity C# naming: PascalCase for classes, structs, enums, public methods, and public properties; "
                "_camelCase or camelCase for private fields.\n"
                "2. Encapsulation: Prefer [SerializeField] private fields instead of public variables for Inspector exposure.\n"
                "3. Performance: Cache component references (e.g., GetComponent<T>()) in Awake() or Start(). Never invoke GetComponent in Update() or FixedUpdate().\n"
                "4. Memory & GC: Avoid instantiating objects, boxing, or allocating arrays inside Update() loops.\n"
                "5. Architecture: Separate core domain gameplay logic from MonoBehaviour view/actor scripts where possible."
            ),
            "source": "Unity Engine Standards",
        }
    ]

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[Dict[str, str], str]:
        """Extract YAML frontmatter key-values and remaining markdown body."""
        meta: Dict[str, str] = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                raw_meta = parts[1]
                body = parts[2].strip()
                for line in raw_meta.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip("\"'")
        return meta, body

    @classmethod
    def detect_project_type(cls, project_path: Optional[str]) -> str:
        """Detect whether target directory is a Unity project, Python project, or generic."""
        if not project_path:
            return "generic"
        p = Path(project_path).resolve()
        if not p.exists():
            return "generic"

        if (p / "Assets").exists() or (p / "ProjectSettings").exists():
            return "unity"

        if (p / "pyproject.toml").exists() or (p / "requirements.txt").exists():
            return "python"

        if (p / "package.json").exists():
            return "javascript"

        if (p / "go.mod").exists():
            return "go"

        if (p / "Cargo.toml").exists():
            return "rust"

        if any(p.glob("*.html")):
            return "web"

        return "generic"

    @classmethod
    def discover_rules(cls, project_path: Optional[str], project_type: str, objective: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect all active rules from global configs, project-specific files, and user-referenced specs."""
        rules: List[Dict[str, Any]] = list(cls.MANDATORY_GLOBAL_RULES)

        if project_type == "unity":
            rules.extend(cls.UNITY_CONSTRAINTS)

        # 1. Global config rules (~/.gemini/config/rules)
        global_config_rules = Path(os.path.expanduser("~/.gemini/config/rules"))
        if global_config_rules.exists() and global_config_rules.is_dir():
            for rule_file in global_config_rules.glob("*.md"):
                try:
                    content = rule_file.read_text(encoding="utf-8")
                    rules.append({
                        "id": f"global_{rule_file.stem}",
                        "title": f"Global Rule: {rule_file.stem}",
                        "content": content.strip(),
                        "source": str(rule_file),
                    })
                except Exception:
                    pass

        # 2. Project-level specs, documentation, and user-referenced guides
        if project_path:
            p = Path(project_path).resolve()
            if p.exists() and p.is_dir():
                # Extract any *.md files mentioned in user's objective (e.g. 'level-editor.md')
                mentioned_md_files = []
                if objective:
                    mentioned_md_files = re.findall(r"[\w\.-]+\.md", objective, re.IGNORECASE)

                ignore_folders = {".git", ".pytest_cache", "Library", "Temp", "PackageCache", "obj", "Build", "Builds"}
                seen_sources = set()

                # Recursively search for all relevant markdown files in project
                for md_file in p.rglob("*.md"):
                    if any(ignored in md_file.parts for ignored in ignore_folders):
                        continue

                    rel_path = str(md_file.relative_to(p)).replace("\\", "/")
                    fname = md_file.name
                    fname_lower = fname.lower()

                    is_explicitly_mentioned = any(fname_lower == m.lower() for m in mentioned_md_files)
                    is_spec_or_rule = (
                        is_explicitly_mentioned
                        or fname in ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", "RULES.md"]
                        or any(kw in fname_lower for kw in ["editor", "spec", "architecture", "design", "guide", "manual", "rule"])
                    )

                    if is_spec_or_rule and rel_path not in seen_sources:
                        seen_sources.add(rel_path)
                        try:
                            content = md_file.read_text(encoding="utf-8", errors="replace")
                            # If explicitly mentioned in objective, give generous capacity and top priority
                            max_len = 8000 if is_explicitly_mentioned else 2500
                            rule_entry = {
                                "id": f"project_{md_file.stem}",
                                "title": f"{'⭐ PRIMARY SPECIFICATION GUIDE' if is_explicitly_mentioned else 'Project Guideline'}: {rel_path}",
                                "content": content.strip()[:max_len],
                                "source": rel_path,
                                "is_primary_spec": is_explicitly_mentioned,
                            }
                            if is_explicitly_mentioned:
                                rules.insert(0, rule_entry)  # Place at the very top of rules!
                            else:
                                rules.append(rule_entry)
                        except Exception:
                            pass

        return rules

    @classmethod
    def discover_skills(cls, project_path: Optional[str]) -> List[Dict[str, Any]]:
        """Find available skills from project workspace and global customizations."""
        skills: List[Dict[str, Any]] = []
        seen_names = set()

        search_locations = []

        # 1. Project-level skills
        if project_path:
            p = Path(project_path).resolve()
            search_locations.append(p / ".agents" / "skills")

        # 2. Global customizations root
        search_locations.append(Path(os.path.expanduser("~/.gemini/config/skills")))

        # 3. Global plugins skills
        plugins_dir = Path(os.path.expanduser("~/.gemini/config/plugins"))
        if plugins_dir.exists():
            for plugin_folder in plugins_dir.iterdir():
                if plugin_folder.is_dir():
                    search_locations.append(plugin_folder / "skills")

        for location in search_locations:
            if not location.exists() or not location.is_dir():
                continue

            for skill_dir in location.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        try:
                            content = skill_file.read_text(encoding="utf-8")
                            meta, body = cls._parse_frontmatter(content)
                            name = meta.get("name", skill_dir.name)
                            if name in seen_names:
                                continue
                            if name in ["ponytail-debt", "ponytail-audit", "ponytail-gain", "ponytail-help"]:
                                continue
                            seen_names.add(name)

                            skills.append({
                                "name": name,
                                "description": meta.get("description", "No description provided."),
                                "instructions": body[:600],
                                "path": str(skill_file),
                            })
                        except Exception:
                            pass

        # 4. Project-level markdown skills with YAML frontmatter (e.g. Assets/BlockHome/level-editor.md)
        if project_path:
            p = Path(project_path).resolve()
            if p.exists() and p.is_dir():
                ignore_folders = {".git", ".pytest_cache", "Library", "Temp", "PackageCache"}
                for md_file in p.rglob("*.md"):
                    if any(ignored in md_file.parts for ignored in ignore_folders):
                        continue
                    try:
                        first_bytes = md_file.read_text(encoding="utf-8", errors="replace")[:600]
                        if first_bytes.startswith("---"):
                            full_text = md_file.read_text(encoding="utf-8", errors="replace")
                            meta, body = cls._parse_frontmatter(full_text)
                            name = meta.get("name")
                            if name and name not in seen_names:
                                seen_names.add(name)
                                skills.append({
                                    "name": name,
                                    "description": meta.get("description", "Custom Project Skill"),
                                    "instructions": body[:3000],
                                    "path": str(md_file),
                                })
                    except Exception:
                        pass

        return skills

    @classmethod
    def ingest(
        cls,
        project_path: Optional[str] = None,
        user_project_type: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform Phase 0 context ingestion and return consolidated context package."""
        resolved_type = user_project_type if user_project_type and user_project_type != "generic" else cls.detect_project_type(project_path)
        rules = cls.discover_rules(project_path, resolved_type, objective=objective)
        skills = cls.discover_skills(project_path)

        discovered_scripts: List[str] = []
        if project_path and resolved_type == "unity":
            p = Path(project_path)
            assets_dir = p / "Assets"
            if assets_dir.exists() and assets_dir.is_dir():
                for cs_file in assets_dir.rglob("*.cs"):
                    rel_p = str(cs_file.relative_to(p)).replace("\\", "/")
                    if "Plugins" not in rel_p and "TutorialInfo" not in rel_p:
                        discovered_scripts.append(rel_p)
                if discovered_scripts:
                    rules.append({
                        "id": "project_existing_scripts",
                        "title": f"Existing Project C# Scripts ({len(discovered_scripts)} found)",
                        "content": "Existing project C# scripts available to inspect and modify:\n" + "\n".join([f"- {s}" for s in discovered_scripts[:60]]),
                        "source": "Project Assets Scan",
                    })

        summary = (
            f"Project: {project_path or 'Sandbox'} | Type: [{resolved_type.upper()}] | "
            f"Ingested Rules: {len(rules)} | Discovered Skills: {len(skills)}"
            + (f" | Existing Scripts: {len(discovered_scripts)}" if discovered_scripts else "")
        )

        return {
            "project_path": project_path,
            "project_type": resolved_type,
            "rules": rules,
            "skills": skills,
            "summary": summary,
            "discovered_scripts": discovered_scripts,
        }
