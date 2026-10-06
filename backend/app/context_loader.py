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
    def scan_project_files(cls, project_path: str, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, str]]:
        """Quickly list non-ignored project files for autocomplete and @ mentions."""
        if not project_path:
            return []
        p = Path(project_path).resolve()
        if not p.exists() or not p.is_dir():
            return []

        ignore_folders = {
            ".git", ".vs", ".idea", "Library", "Temp", "PackageCache", "obj",
            "Build", "Builds", "node_modules", "bin", "logs", "__pycache__", ".pytest_cache"
        }
        allowed_extensions = {
            ".cs", ".md", ".uxml", ".uss", ".json", ".shader",
            ".ts", ".tsx", ".js", ".py", ".html", ".css", ".yaml", ".yml", ".txt"
        }

        matched_files = []
        q_lower = query.lower().strip() if query else ""

        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in ignore_folders and not d.startswith(".")]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext not in allowed_extensions:
                    continue

                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(p)).replace("\\", "/")
                name_lower = file.lower()
                rel_lower = rel_path.lower()

                if q_lower:
                    if q_lower not in name_lower and q_lower not in rel_lower:
                        continue

                is_exact = (name_lower == q_lower or Path(file).stem.lower() == q_lower)
                starts_with = name_lower.startswith(q_lower) if q_lower else False
                score = 2 if is_exact else (1 if starts_with else 0)

                matched_files.append({
                    "path": rel_path,
                    "name": file,
                    "ext": ext.lstrip("."),
                    "score": score,
                })

        matched_files.sort(key=lambda x: (-x["score"], len(x["path"]), x["path"]))
        return [{k: v for k, v in item.items() if k != "score"} for item in matched_files[:limit]]

    @classmethod
    def extract_referenced_files(cls, project_path: Optional[str], objective: Optional[str]) -> Dict[str, List[str]]:
        """
        Detect any files explicitly or implicitly referenced in objective:
        1. @ mentions (e.g. @Assets/BlockHome/level-editor.md or @level-editor.md)
        2. Words with file extensions (e.g. BlockHomeLevelEditorWindow.Toolbar.cs, level-editor.md)
        3. Exact matching of filename stems in the project (e.g. BlockHomeLevelEditorWindow, level-editor)
        Returns:
            {"spec_files": [...], "code_files": [...]}
        """
        if not project_path or not objective:
            return {"spec_files": [], "code_files": []}

        p = Path(project_path).resolve()
        if not p.exists() or not p.is_dir():
            return {"spec_files": [], "code_files": []}

        at_mentions = re.findall(r"@([\w\./\\-]+)", objective)
        ext_tokens = re.findall(r"\b([\w\.-]+\.(?:md|cs|uxml|uss|json|shader|py|ts|tsx|js|html|txt))\b", objective, re.IGNORECASE)
        stem_tokens = re.findall(r"\b([A-Za-z0-9_-]{4,})\b", objective)

        candidates = set()
        for m in at_mentions:
            clean_m = m.replace("\\", "/").strip("./")
            candidates.add(clean_m)
            candidates.add(Path(clean_m).name)
        for t in ext_tokens:
            candidates.add(t)
            candidates.add(Path(t).name)
        for s in stem_tokens:
            candidates.add(s)

        ignore_folders = {
            ".git", ".vs", ".idea", "Library", "Temp", "PackageCache", "obj",
            "Build", "Builds", "node_modules", "bin", "logs"
        }
        valid_code_exts = {".cs", ".uxml", ".uss", ".json", ".shader", ".py", ".ts", ".tsx", ".js", ".html", ".css"}
        generic_stem_words = {
            "level", "editor", "game", "system", "tool", "file", "code", "scene",
            "view", "data", "test", "demo", "play", "home", "block", "script", "manager"
        }

        matched_specs = []
        matched_code = []
        seen_paths = set()

        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in ignore_folders and not d.startswith(".")]
            for file in files:
                if file.endswith(".meta"):
                    continue

                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(p)).replace("\\", "/")
                fname = file
                fname_lower = fname.lower()
                stem_lower = Path(file).stem.lower()
                ext_lower = Path(file).suffix.lower()

                matched = False
                for c in candidates:
                    c_lower = c.lower()
                    # 1. Exact relative path
                    if c_lower == rel_path.lower():
                        matched = True
                        break
                    # 2. Exact filename with extension
                    if c_lower == fname_lower:
                        matched = True
                        break
                    # 3. Exact stem match for compound/specific names (excluding generic single words)
                    if (
                        "." not in c
                        and c_lower == stem_lower
                        and len(c) >= 5
                        and c_lower not in generic_stem_words
                        and ext_lower in (valid_code_exts | {".md", ".txt"})
                    ):
                        matched = True
                        break

                if matched and rel_path not in seen_paths:
                    seen_paths.add(rel_path)
                    if ext_lower in [".md", ".txt"]:
                        matched_specs.append(rel_path)
                    elif ext_lower in valid_code_exts:
                        matched_code.append(rel_path)

        return {"spec_files": matched_specs, "code_files": matched_code}

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
                referenced = cls.extract_referenced_files(project_path, objective)
                referenced_specs = set(referenced["spec_files"])

                ignore_folders = {".git", ".pytest_cache", "Library", "Temp", "PackageCache", "obj", "Build", "Builds"}
                seen_sources = set()

                # First load explicitly referenced spec files with maximum priority & full content
                for ref_spec in referenced_specs:
                    spec_path = p / ref_spec
                    if spec_path.exists() and ref_spec not in seen_sources:
                        seen_sources.add(ref_spec)
                        try:
                            content = spec_path.read_text(encoding="utf-8", errors="replace")
                            rules.insert(0, {
                                "id": f"project_{spec_path.stem}",
                                "title": f"⭐ PRIMARY SPECIFICATION GUIDE: {ref_spec}",
                                "content": content.strip()[:10000],
                                "source": ref_spec,
                                "is_primary_spec": True,
                            })
                        except Exception:
                            pass

                # Recursively search for other relevant markdown files in project
                for md_file in p.rglob("*.md"):
                    if any(ignored in md_file.parts for ignored in ignore_folders):
                        continue

                    rel_path = str(md_file.relative_to(p)).replace("\\", "/")
                    if rel_path in seen_sources:
                        continue

                    fname = md_file.name
                    fname_lower = fname.lower()

                    is_spec_or_rule = (
                        fname in ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", "RULES.md"]
                        or any(kw in fname_lower for kw in ["editor", "spec", "architecture", "design", "guide", "manual", "rule"])
                    )

                    if is_spec_or_rule and rel_path not in seen_sources:
                        seen_sources.add(rel_path)
                        try:
                            content = md_file.read_text(encoding="utf-8", errors="replace")
                            rules.append({
                                "id": f"project_{md_file.stem}",
                                "title": f"Project Guideline: {rel_path}",
                                "content": content.strip()[:2500],
                                "source": rel_path,
                                "is_primary_spec": False,
                            })
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
        discovered_ui: List[str] = []
        if project_path and resolved_type == "unity":
            p = Path(project_path)
            assets_dir = p / "Assets"
            if assets_dir.exists() and assets_dir.is_dir():
                for ext in ["*.cs", "*.uxml", "*.uss"]:
                    for f in assets_dir.rglob(ext):
                        rel_p = str(f.relative_to(p)).replace("\\", "/")
                        if "Plugins" not in rel_p and "TutorialInfo" not in rel_p:
                            if ext == "*.cs":
                                discovered_scripts.append(rel_p)
                            else:
                                discovered_ui.append(rel_p)

                if discovered_scripts:
                    rules.append({
                        "id": "project_existing_scripts",
                        "title": f"Existing Project C# Scripts ({len(discovered_scripts)} found)",
                        "content": "Existing project C# scripts available to inspect and modify:\n" + "\n".join([f"- {s}" for s in discovered_scripts[:80]]),
                        "source": "Project Assets Scan",
                    })

                editor_scripts = [s for s in discovered_scripts if "editor" in s.lower()]
                if editor_scripts:
                    rules.append({
                        "id": "project_existing_editor_scripts",
                        "title": f"Existing Unity Editor Scripts ({len(editor_scripts)} found)",
                        "content": "Existing Editor tool scripts in the project (DO NOT duplicate, extend these):\n" + "\n".join([f"- {s}" for s in editor_scripts]),
                        "source": "Project Editor Scan",
                    })

        referenced = cls.extract_referenced_files(project_path, objective)
        explicit_target_files = referenced["code_files"]
        explicit_spec_files = referenced["spec_files"]

        summary = (
            f"Project: {project_path or 'Sandbox'} | Type: [{resolved_type.upper()}] | "
            f"Ingested Rules: {len(rules)} | Discovered Skills: {len(skills)}"
            + (f" | Existing Scripts: {len(discovered_scripts)}" if discovered_scripts else "")
            + (f" | UI Assets: {len(discovered_ui)}" if discovered_ui else "")
            + (f" | Referenced Targets: {len(explicit_target_files)}" if explicit_target_files else "")
            + (f" | Referenced Specs: {len(explicit_spec_files)}" if explicit_spec_files else "")
        )

        return {
            "project_path": project_path,
            "project_type": resolved_type,
            "rules": rules,
            "skills": skills,
            "summary": summary,
            "discovered_scripts": discovered_scripts,
            "discovered_ui": discovered_ui,
            "explicit_target_files": explicit_target_files,
            "explicit_spec_files": explicit_spec_files,
        }
