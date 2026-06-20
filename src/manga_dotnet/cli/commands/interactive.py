"""Interactive shell — ``mdnet shell``."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.box import ROUNDED

from manga_dotnet.cli.error_handler import handle_error
from manga_dotnet.cli.widgets.splash import show_splash

# Shared client instance to avoid opening a new browser every time
_shared_client = None


def _get_client():
    """Get or create a shared API client (reuses the same browser)."""
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    from manga_dotnet.api.client import MangaDotNetClient
    from manga_dotnet.core.config import Config
    config = Config.load()
    _shared_client = MangaDotNetClient(config)
    _shared_client.initialize()
    return _shared_client


def _close_client():
    """Close the shared client."""
    global _shared_client
    if _shared_client is not None:
        try:
            _shared_client.close()
        except Exception:
            pass
        _shared_client = None


def _extract_manga_id(value: str) -> int | None:
    """Extract manga ID from a URL or plain number."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    match = re.search(r"mangadot\.net/(?:manga/)?(\d+)", value, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _show_main_menu(console: Console) -> str:
    """Display the main menu and return the user's choice."""
    console.print()
    console.print(Panel(
        "[bold magenta]📚 MangaDotNet Interactive Shell[/bold magenta]\n\n"
        "  [bold]1.[/bold] 🔍 Search by name\n"
        "  [bold]2.[/bold] 🔗 Search by URL / Manga ID\n"
        "  [bold]3.[/bold] 📖 Browse manga (chapters & volumes)\n"
        "  [bold]4.[/bold] ⬇️  Download manga\n"
        "  [bold]5.[/bold] 📚 Local library\n"
        "  [bold]6.[/bold] 📋 Download history\n"
        "  [bold]7.[/bold] ⚙️  Settings\n"
        "  [bold]8.[/bold] 🔴 Auto update\n"
        "  [bold]9.[/bold] ❌ Exit",
        title="Main Menu",
        box=ROUNDED,
        border_style="magenta",
    ))
    return Prompt.ask("Select", choices=[str(i) for i in range(1, 10)], default="1")


def _action_search(console: Console) -> None:
    """Search for manga by name."""
    query = Prompt.ask("[bold]Search query[/bold]")
    if not query.strip():
        return

    try:
        with console.status("[bold purple]Searching..."):
            from manga_dotnet.api.search import SearchAPI
            client = _get_client()
            search_api = SearchAPI(client)
            results = search_api.search(query, limit=20)

        if not results:
            console.print("[warning]No results found.[/warning]")
            return

        table = Table(title=f"🔍 Results: \"{query}\"", show_header=True, header_style="bold purple")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Status", width=10)
        table.add_column("Chapters", justify="right", width=8)
        table.add_column("Rating", justify="right", width=6)

        for idx, manga in enumerate(results, 1):
            table.add_row(
                str(idx), manga.title, manga.status or "—",
                str(manga.chapter_count) if manga.chapter_count else "—",
                f"{manga.rating:.1f}" if manga.rating else "—",
            )

        console.print(table)

        if Confirm.ask("View details?", default=False):
            choice = IntPrompt.ask("Enter # (0 to skip)", default=0)
            if 1 <= choice <= len(results):
                _action_show_info(console, results[choice - 1].id)

    except Exception as e:
        handle_error(console, e)


def _action_search_by_url(console: Console) -> None:
    """Search by URL or manga ID."""
    value = Prompt.ask("[bold]Enter manga ID or URL[/bold]")
    manga_id = _extract_manga_id(value)
    if manga_id is None:
        console.print("[error]Could not extract manga ID.[/error]")
        return
    _action_show_info(console, manga_id)


def _action_show_info(console: Console, manga_id: int) -> None:
    """Fetch and display manga info with follow-up options."""
    try:
        with console.status("[bold purple]Fetching info..."):
            from manga_dotnet.api.manga import MangaAPI
            client = _get_client()
            manga_api = MangaAPI(client)
            manga = manga_api.get_info(manga_id)

        from manga_dotnet.cli.widgets.manga_panel import create_manga_panel
        console.print(create_manga_panel(manga))

        # Sub-menu after viewing info
        while True:
            console.print()
            console.print("[bold]What next?[/bold]  [dim]1[/dim]=Browse chapters  "
                          "[dim]2[/dim]=Download  [dim]3[/dim]=Back to menu")
            sub = Prompt.ask("Select", choices=["1", "2", "3"], default="3")
            if sub == "1":
                chapters = _action_browse_internal(console, manga_id, client, manga)
                if chapters:
                    _action_download_internal(console, manga_id, client, manga, pre_selected=chapters)
            elif sub == "2":
                _action_download_internal(console, manga_id, client, manga)
            else:
                break

    except Exception as e:
        handle_error(console, e)


def _action_browse(console: Console) -> None:
    """Browse chapters and volumes for a manga."""
    value = Prompt.ask("[bold]Enter manga ID or URL[/bold]")
    manga_id = _extract_manga_id(value)
    if manga_id is None:
        console.print("[error]Could not extract manga ID.[/error]")
        return
    chapters = _action_browse_internal(console, manga_id, None, None)
    # If user chose to download from browse, chapters will be a non-None list
    # but we need the client/manga too — so re-fetch is avoided by passing through
    # Actually _action_download_internal needs client+manga, so we just call it
    # and let it re-use the shared client. The chapters list is the selection.
    if chapters:
        _action_download_internal(console, manga_id, None, None, pre_selected=chapters)


def _action_browse_internal(console: Console, manga_id: int, client=None, manga=None) -> list | None:
    """Internal browse with optional pre-fetched client/manga. Returns selected chapters or None."""
    try:
        from manga_dotnet.api.manga import MangaAPI
        from manga_dotnet.api.chapters import ChapterAPI
        from manga_dotnet.core.engine import ChapterFilter
        from manga_dotnet.core.config import Config

        if client is None:
            client = _get_client()

        with console.status("[bold purple]Fetching manga data..."):
            manga_api = MangaAPI(client)
            chapter_api = ChapterAPI(client)
            cf = ChapterFilter()
            config = Config.load()

            if manga is None:
                manga = manga_api.get_info(manga_id)
            all_chapters = chapter_api.get_chapters(manga_id)

        if not all_chapters:
            console.print("[warning]No chapters found.[/warning]")
            return None

        console.print(f"\n[bold]{manga.title}[/bold] — {len(all_chapters)} raw chapters")

        # Show available languages
        langs = cf.get_available_languages(all_chapters)
        if langs:
            lang_str = "  ".join(f"{l['code']}({l['count']})" for l in langs[:8])
            console.print(f"[dim]Languages: {lang_str}[/dim]")

        # Show available groups
        groups = cf.get_available_groups(all_chapters)
        if groups:
            group_str = "  ".join(f"{g['name']}({g['chapter_count']})" for g in groups[:5])
            console.print(f"[dim]Groups: {group_str}[/dim]")

        # Filtering
        console.print()
        language = Prompt.ask("[bold]Language filter[/bold]", default="all")
        if language.lower() == "all":
            language = None
        group_filter = Prompt.ask("[bold]Group filter[/bold]", default="all")
        if group_filter.lower() == "all":
            group_filter = None

        deduped = cf.filter_and_deduplicate(
            all_chapters, language=language, group_name=group_filter,
            prefer_user_uploaded=config.prefer_user_uploaded,
        )
        console.print(f"\n[info]{len(deduped)} chapters after filtering[/info]")

        # Chapter table
        table = Table(title=f"📖 {manga.title} — Chapters", show_header=True, header_style="bold purple")
        table.add_column("Idx", style="dim", width=5)
        table.add_column("Chapter", style="bold", width=12)
        table.add_column("Title", max_width=30)
        table.add_column("Pages", justify="right", width=6)
        table.add_column("Group", max_width=20)
        table.add_column("Lang", width=4)
        table.add_column("Source", width=6)

        for idx, ch in enumerate(deduped, 1):
            table.add_row(
                str(idx), f"Ch. {ch.chapter_number:g}", ch.chapter_title or "—",
                str(ch.page_count), ch.group_name or "—", ch.language, ch.source or "—",
            )
        console.print(table)

        # Volume listing
        if Confirm.ask("\nShow volumes?", default=False):
            _action_show_volumes(console, manga_id, client)

        # Post-browse options
        console.print()
        console.print("[bold]Download selection:[/bold]")
        console.print("  [dim]1[/dim]  All chapters")
        console.print("  [dim]2[/dim]  Chapter range (e.g. 1-50)")
        console.print("  [dim]3[/dim]  Specific chapters (e.g. 2,5,10)")
        console.print("  [dim]4[/dim]  Latest N chapters")
        console.print("  [dim]5[/dim]  Go back (no download)")

        sub = Prompt.ask("Select", choices=["1", "2", "3", "4", "5"], default="1")

        if sub == "1":
            return deduped
        elif sub == "2":
            range_str = Prompt.ask("Chapter numbers range (e.g. 5-50)")
            nums: set[int] = set()
            for part in range_str.split(","):
                part = part.strip()
                if "-" in part:
                    s, e = part.split("-", 1)
                    nums.update(range(int(s), int(e) + 1))
                elif part.isdigit():
                    nums.add(int(part))
            selected = [c for c in deduped if int(c.chapter_number) in nums]
            if not selected:
                console.print("[warning]No chapters matched that range.[/warning]")
                return None
            console.print(f"[info]Selected {len(selected)} chapters[/info]")
            return selected
        elif sub == "3":
            ch_str = Prompt.ask("Chapter numbers (e.g. 4,7,10 or 7-9)")
            nums_i: set[int] = set()
            for part in ch_str.split(","):
                part = part.strip()
                if "-" in part:
                    try:
                        s, e = part.split("-", 1)
                        nums_i.update(range(int(s), int(e) + 1))
                    except ValueError:
                        pass
                elif part.isdigit():
                    nums_i.add(int(part))
            selected = [c for c in deduped if int(c.chapter_number) in nums_i]
            if not selected:
                console.print("[warning]No chapters matched.[/warning]")
                return None
            console.print(f"[info]Selected {len(selected)} chapters[/info]")
            return selected
        elif sub == "4":
            n = IntPrompt.ask("How many latest?", default=5)
            selected = sorted(deduped, key=lambda c: c.chapter_number)[-n:]
            console.print(f"[info]Selected {len(selected)} latest chapters[/info]")
            return selected
        else:
            return None

    except Exception as e:
        handle_error(console, e)
        return None


def _action_show_volumes(console: Console, manga_id: int, client=None) -> None:
    """Fetch and display volumes."""
    try:
        if client is None:
            client = _get_client()
        with console.status("[bold purple]Fetching volumes..."):
            raw_volumes = client.get_volumes(manga_id)
        if not raw_volumes:
            console.print("[warning]No volumes found.[/warning]")
            return
        table = Table(title="📦 Volumes", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Volume", style="bold", width=10)
        table.add_column("Pages", justify="right", width=6)
        table.add_column("Group", max_width=25)
        for idx, vol in enumerate(raw_volumes, 1):
            table.add_row(str(idx), f"Vol. {vol.get('volume_number', '?')}",
                          str(vol.get("page_count", 0)), vol.get("group_name") or "—")
        console.print(table)
    except Exception as e:
        handle_error(console, e)


def _action_download(console: Console) -> None:
    """Download manga chapters with full filtering."""
    value = Prompt.ask("[bold]Enter manga ID or URL[/bold]")
    manga_id = _extract_manga_id(value)
    if manga_id is None:
        console.print("[error]Could not extract manga ID.[/error]")
        return
    _action_download_internal(console, manga_id, None, None)


def _action_download_internal(console: Console, manga_id: int, client=None, manga=None, pre_selected=None) -> None:
    """Internal download with optional pre-fetched client/manga/chapters."""
    try:
        from manga_dotnet.api.manga import MangaAPI
        from manga_dotnet.api.chapters import ChapterAPI
        from manga_dotnet.core.engine import ChapterFilter
        from manga_dotnet.core.config import Config

        if client is None:
            client = _get_client()

        with console.status("[bold purple]Fetching manga data..."):
            manga_api = MangaAPI(client)
            chapter_api = ChapterAPI(client)
            cf = ChapterFilter()
            config = Config.load()
            if manga is None:
                manga = manga_api.get_info(manga_id)
            all_chapters = chapter_api.get_chapters(manga_id)

        if not all_chapters:
            console.print("[warning]No chapters found.[/warning]")
            return

        console.print(f"\n[bold]{manga.title}[/bold] — {len(all_chapters)} raw chapters")

        if pre_selected is not None and len(pre_selected) > 0:
            # Chapters were already selected during browse — skip filtering/selection
            selected = pre_selected
            console.print(f"[info]Using {len(selected)} chapters from browse selection[/info]")
        else:
            # Filtering
            language = Prompt.ask("[bold]Language filter[/bold]", default="all")
            if language.lower() == "all":
                language = None
            group_filter = Prompt.ask("[bold]Group filter[/bold]", default="all")
            if group_filter.lower() == "all":
                group_filter = None

            deduped = cf.filter_and_deduplicate(
                all_chapters, language=language, group_name=group_filter,
                prefer_user_uploaded=config.prefer_user_uploaded,
            )
            console.print(f"[info]{len(deduped)} chapters available[/info]")

            # Selection mode
            console.print("\n[bold]Selection:[/bold]")
            console.print("  [dim]1[/dim]  All chapters")
            console.print("  [dim]2[/dim]  Latest N chapters")
            console.print("  [dim]3[/dim]  Chapter range (e.g. 1-50)")
            console.print("  [dim]4[/dim]  Specific chapters (e.g. 1,5,10)")
            console.print("  [dim]5[/dim]  By volume")

            mode = Prompt.ask("Mode", choices=["1", "2", "3", "4", "5"], default="1")

            if mode == "1":
                selected = deduped
            elif mode == "2":
                n = IntPrompt.ask("How many latest?", default=5)
                selected = sorted(deduped, key=lambda c: c.chapter_number)[-n:]
            elif mode == "3":
                range_str = Prompt.ask("Chapter numbers range (e.g. 5-50)")
                nums: set[int] = set()
                for part in range_str.split(","):
                    part = part.strip()
                    if "-" in part:
                        s, e = part.split("-", 1)
                        nums.update(range(int(s), int(e) + 1))
                    elif part.isdigit():
                        nums.add(int(part))
                selected = [c for c in deduped if int(c.chapter_number) in nums]
            elif mode == "4":
                ch_str = Prompt.ask("Chapters (e.g. 1,5,10)")
                nums_i: set[int] = set()
                for part in ch_str.split(","):
                    if part.strip().isdigit():
                        nums_i.add(int(part.strip()))
                selected = [c for c in deduped if int(c.chapter_number) in nums_i]
            elif mode == "5":
                vol_str = Prompt.ask("Volumes (e.g. 1,2,3)")
                vol_nums: set[float] = set()
                for part in vol_str.split(","):
                    try:
                        vol_nums.add(float(part.strip()))
                    except ValueError:
                        pass
                selected = [c for c in deduped if c.volume_number and c.volume_number in vol_nums]
            else:
                selected = deduped

        if not selected:
            console.print("[error]No chapters selected.[/error]")
            return

        # Format
        fmt = Prompt.ask(
            "[bold]Format[/bold]", choices=["cbz", "zip", "pdf", "images", "folder"],
            default=config.default_format,
        )
        delete_images = Confirm.ask("Delete images after export?", default=False)

        total_pages = sum(c.page_count for c in selected)
        console.print(f"\n[info]{len(selected)} ch, {total_pages} pages, format: {fmt}[/info]")

        if not Confirm.ask("Proceed?", default=True):
            return

        # Download
        from manga_dotnet.api.images import ImageAPI
        from manga_dotnet.export.cleanup import get_exporter
        import asyncio, time

        image_api = ImageAPI(client)
        exporter = get_exporter(fmt)
        output_dir = config.output_dir
        safe_title = "".join(c for c in manga.title if c.isalnum() or c in " -_").strip().replace(" ", "_")
        max_retries = config.download.max_retries
        retry_delay = config.download.retry_delay

        downloaded = 0
        failed = 0
        start_time = time.time()

        for ch in selected:
            ch_num = ch.chapter_number
            try:
                with console.status(f"[bold purple]Ch. {ch_num:g}..."):
                    ch_images = image_api.get_images(ch.id)
                if not ch_images or not ch_images.images:
                    console.print(f"[warning]Ch. {ch_num:g}: No images[/warning]")
                    failed += 1
                    continue

                page_data = []
                for img in ch_images.images:
                    data = None
                    for attempt in range(max_retries + 1):
                        try:
                            data = image_api.download_image(img.full_url)
                            if data:
                                break
                        except Exception:
                            if attempt < max_retries:
                                time.sleep(retry_delay)
                    if data:
                        page_data.append((img, data))

                if not page_data:
                    console.print(f"[warning]Ch. {ch_num:g}: All pages failed[/warning]")
                    failed += 1
                    continue

                raw_images = [d for _, d in page_data]
                chapter_dir = output_dir / safe_title / f"Chapter_{ch_num:g}"
                chapter_dir.mkdir(parents=True, exist_ok=True)
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(exporter.export(
                        images=raw_images, output_dir=chapter_dir,
                        filename=f"Chapter_{ch_num:g}",
                        metadata={"chapter_id": ch.id, "chapter_number": ch_num, "manga_title": manga.title},
                    ))
                finally:
                    loop.close()

                if fmt not in ("images", "folder") and not delete_images:
                    from manga_dotnet.export.base import detect_extension
                    for p_idx, (_, img_bytes) in enumerate(page_data):
                        ext = detect_extension(img_bytes)
                        (chapter_dir / f"{p_idx + 1:04d}{ext}").write_bytes(img_bytes)

                console.print(f"[success]✓ Ch. {ch_num:g} — {len(page_data)} pages[/success]")
                downloaded += 1

            except Exception as e:
                console.print(f"[error]✗ Ch. {ch_num:g}: {e}[/error]")
                failed += 1

        elapsed = time.time() - start_time
        console.print()
        if failed == 0:
            console.print(Panel(
                f"[success]✓ Done![/success]  {downloaded} ch, {elapsed:.1f}s\n  → {output_dir / safe_title}",
                box=ROUNDED, border_style="green"))
        else:
            console.print(Panel(
                f"[warning]⚠ Completed[/warning]  OK:{downloaded} Failed:{failed}  {elapsed:.1f}s",
                box=ROUNDED, border_style="yellow"))

        # Record history
        try:
            from manga_dotnet.core.history import LibraryManager
            nums = [c.chapter_number for c in selected]
            cr = f"Ch. {min(nums):g}-{max(nums):g}" if len(nums) > 1 else f"Ch. {nums[0]:g}"
            LibraryManager().record_download(
                manga_id=manga_id, manga_title=manga.title, chapter_range=cr,
                export_format=fmt, chapters_downloaded=downloaded,
                status="success" if failed == 0 else "partial")
        except Exception:
            pass

    except Exception as e:
        handle_error(console, e)


def _action_library(console: Console) -> None:
    """Show local library."""
    try:
        from manga_dotnet.core.history import LibraryManager
        manager = LibraryManager()
        entries = manager.scan_directory()
        if not entries:
            console.print("[dim]No manga found in library.[/dim]")
            return
        from manga_dotnet.utils.filesystem import format_size
        table = Table(title="📚 Local Library", show_header=True, header_style="bold purple")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Chapters", justify="right")
        table.add_column("Size", justify="right", style="dim")
        table.add_column("Last Downloaded", style="dim")
        for idx, entry in enumerate(entries, 1):
            table.add_row(str(idx), entry.title, str(entry.chapter_count),
                          format_size(entry.total_size_bytes),
                          entry.last_downloaded[:10] if entry.last_downloaded else "—")
        console.print(table)
        total_size = sum(e.total_size_bytes for e in entries)
        console.print(f"\n[dim]{len(entries)} manga — {format_size(total_size)} total[/dim]")
    except Exception as e:
        handle_error(console, e)


def _action_history(console: Console) -> None:
    """Show download history."""
    try:
        from manga_dotnet.core.history import LibraryManager
        manager = LibraryManager()
        history = manager.get_history(limit=20)
        if not history:
            console.print("[dim]No download history.[/dim]")
            return
        table = Table(title="📋 Download History", show_header=True, header_style="bold purple")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Chapters")
        table.add_column("Format")
        table.add_column("Date", style="dim")
        table.add_column("Status")
        for idx, entry in enumerate(history, 1):
            ss = "green" if entry.status == "success" else "yellow" if entry.status == "partial" else "red"
            table.add_row(str(idx), entry.manga_title, entry.chapter_range,
                          entry.export_format.upper(), entry.timestamp[:10],
                          f"[{ss}]{entry.status}[/{ss}]")
        console.print(table)
    except Exception as e:
        handle_error(console, e)


# Settings metadata: key -> (display_name, description, valid_values)
_SETTINGS_META = {
    "output_dir":          ("Output directory",     "Where downloaded manga is saved", None),
    "default_format":      ("Default format",        "Export format for downloads", ["cbz", "zip", "pdf", "images", "folder"]),
    "default_language":    ("Default language",      "Language filter (e.g. en, ko, all)", None),
    "download.max_concurrent_chapters":  ("Max concurrent chapters", "Chapters downloaded in parallel per manga", None),
    "download.max_concurrent_images":    ("Max concurrent images",   "Images downloaded in parallel per chapter", None),
    "download.max_concurrent_downloads": ("Max concurrent downloads", "Number of manga downloaded simultaneously", None),
    "download.max_retries":              ("Max retries",             "Retry attempts for failed downloads", None),
    "quality.delete_images_after_export": ("Delete images after export", "Remove raw images after creating archive", ["True", "False"]),
    "gui.theme":           ("GUI theme",             "Color theme for the GUI", ["dark", "light", "midnight"]),
}


def _action_settings(console: Console) -> None:
    """Show and edit settings with indexed options and value hints."""
    from manga_dotnet.core.config import Config
    config = Config.load()

    keys = list(_SETTINGS_META.keys())

    while True:
        table = Table(title="⚙️ Settings", show_header=True, header_style="bold purple")
        table.add_column("#", style="dim", width=4)
        table.add_column("Setting", style="bold")
        table.add_column("Value")
        table.add_column("Description", max_width=35, style="dim")

        for idx, key in enumerate(keys, 1):
            meta = _SETTINGS_META[key]
            val = config.get(key)
            val_str = str(val) if val is not None else "—"
            if len(val_str) > 30:
                val_str = val_str[:27] + "..."
            table.add_row(str(idx), meta[0], val_str, meta[1])

        console.print(table)
        console.print(f"\n[dim]Enter a number (1-{len(keys)}) to edit, or 0 to go back[/dim]")

        choice = IntPrompt.ask("Select", default=0)
        if choice == 0:
            break
        if choice < 1 or choice > len(keys):
            console.print("[error]Invalid selection.[/error]")
            continue

        key = keys[choice - 1]
        meta = _SETTINGS_META[key]
        current_val = config.get(key)

        console.print(f"\n[bold]{meta[0]}[/bold]")
        console.print(f"[dim]{meta[1]}[/dim]")
        console.print(f"[dim]Current: {current_val}[/dim]")
        if meta[2]:
            console.print(f"[dim]Valid values: {', '.join(meta[2])}[/dim]")

        new_val = Prompt.ask("New value (empty to cancel)", default="")
        if not new_val.strip():
            continue

        try:
            if meta[2] and new_val.lower() in ("true", "false"):
                config.set(key, new_val.lower() == "true")
            elif isinstance(current_val, bool):
                config.set(key, new_val.lower() == "true")
            elif isinstance(current_val, int):
                config.set(key, int(new_val))
            elif isinstance(current_val, float):
                config.set(key, float(new_val))
            else:
                config.set(key, new_val)
            config.save()
            console.print(f"[success]✓ {meta[0]} = {config.get(key)}[/success]")
        except (KeyError, ValueError) as e:
            console.print(f"[error]Invalid value: {e}[/error]")


def _action_updates(console: Console) -> None:
    """Auto update — git pull latest from GitHub."""
    try:
        from manga_dotnet.core.updates import check_for_updates, auto_update, get_current_version, get_local_commit

        version = get_current_version()
        local = get_local_commit()
        console.print(f"\n[bold]MangaDotNet Downloader[/bold] v{version} (commit: {local})")
        console.print(f"[dim]Repo: {__import__('manga_dotnet.core.updates', fromlist=['GITHUB_REPO']).GITHUB_REPO}[/dim]")

        # Check for updates
        with console.status("[bold purple]Checking for updates..."):
            check = check_for_updates()

        console.print(f"\n[info]{check['message']}[/info]")

        if check["update_available"]:
            if Confirm.ask("Update now?", default=True):
                with console.status("[bold purple]Pulling latest changes..."):
                    result = auto_update()
                if result["success"]:
                    console.print(f"[success]{result['message']}[/success]")
                    if result["pulled"]:
                        console.print("\n[warning]⚠ Restart the application to apply updates.[/warning]")
                else:
                    console.print(f"[error]{result['message']}[/error]")
        else:
            if Confirm.ask("Force pull anyway?", default=False):
                with console.status("[bold purple]Pulling..."):
                    result = auto_update(force=True)
                console.print(f"[success]{result['message']}[/success]" if result["success"] else f"[error]{result['message']}[/error]")

    except Exception as e:
        handle_error(console, e)


def interactive_shell() -> None:
    """Full interactive TUI mode with menu-driven interface."""
    console = Console()
    show_splash(console)

    actions = {
        "1": _action_search,
        "2": _action_search_by_url,
        "3": _action_browse,
        "4": _action_download,
        "5": _action_library,
        "6": _action_history,
        "7": _action_settings,
        "8": _action_updates,
    }

    try:
        while True:
            try:
                choice = _show_main_menu(console)
                if choice == "9":
                    console.print("[info]Goodbye! 👋[/info]")
                    break
                action = actions.get(choice)
                if action:
                    action(console)
            except KeyboardInterrupt:
                console.print("\n[dim]Use 9 to exit.[/dim]")
                continue
            except EOFError:
                console.print("\n[info]Goodbye! 👋[/info]")
                break
            except SystemExit:
                continue
    finally:
        _close_client()
