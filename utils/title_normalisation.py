import re
from rekordbox_mcp.models import Track
from rekordbox.rekordbox import Rekordbox

async def normalise_rekordbox_playlists():
    rb = Rekordbox()
    await rb.start_rekordbox_connection()
    playlists = await rb.get_playlists()
    for playlist in playlists:
        tracks = await rb.get_tracks(playlist)
        for track in tracks:
            artist, title = normalise_track_metadata(track)
            print(f"Updating to: {title} by {artist}")
            await rb.update_track(track.id, title, artist)
            
def normalise_track_metadata(track: Track) -> tuple[str, str]:
    original_title = track.title.strip()
    original_artist = (track.artist or "").strip()

    title = original_title
    artist = ""

    artist_field_is_bad = False

    if original_artist and original_artist.casefold() == original_title.casefold():
        original_artist = ""
        artist_field_is_bad = True

    title = normalise_braces(title)
    title = fix_malformed_brackets(title)
    title = normalise_title_edges(title)

    if original_artist:
        title = remove_existing_artist_prefix(title, original_artist)

    if not original_artist:
        extracted_artist = extract_artist_name(title)
        if extracted_artist:
            artist = extracted_artist
            title = remove_artist_prefix(title)
        elif artist_field_is_bad:
            artist = ""

    title = normalise_no_intro(title)
    title = normalise_intro_versions(title)
    title = fix_malformed_brackets(title)
    title = normalise_whitespace(title)

    if not title:
        return artist, original_title

    return artist, title

def remove_existing_artist_prefix(title: str, artist: str) -> str:
    title = title.strip()
    artist = artist.strip()

    if not title or not artist:
        return title

    # Exact artist prefix:
    # "LMFAO - Party Rock Anthem" -> "Party Rock Anthem"
    pattern = rf"^{re.escape(artist)}\s*-\s*"

    return re.sub(pattern, "", title, flags=re.IGNORECASE).strip()



def extract_artist_name(title: str) -> str | None:
    title = title.strip()

    if " - " not in title:
        return None

    artist_part, title_part = title.split(" - ", 1)
    artist_part = normalise_whitespace(artist_part)

    if not artist_part or not title_part.strip():
        return None

    if re.fullmatch(r"\d+", artist_part):
        return None

    if re.fullmatch(r"\d{1,2}[AB]", artist_part, flags=re.IGNORECASE):
        return None

    # Avoid treating broken leading dash cases as artist extraction
    if artist_part.startswith("-"):
        return None

    return artist_part

def remove_artist_prefix(title: str) -> str:
    """
    Turns:
        Artist - Song Title
    into:
        Song Title
    """
    title = title.strip()

    if " - " not in title:
        return title

    artist_part, title_part = title.split(" - ", 1)

    if re.fullmatch(r"\d+", artist_part.strip()):
        return title

    if re.fullmatch(r"\d{1,2}[AB]", artist_part.strip(), flags=re.IGNORECASE):
        return title

    return title_part.strip()

def normalise_braces( title: str) -> str:
        title = title.replace("[", "(")
        title = title.replace("]", ")")
        return title


def fix_malformed_brackets(title: str) -> str:
    title = title.strip()

    # Remove extra closing brackets at the end:
    # "Crazy In Love (Intro) Radio)" -> "Crazy In Love (Intro) Radio"
    while title.endswith(")") and title.count(")") > title.count("("):
        title = title[:-1].rstrip()

    # Close missing final bracket:
    # "James Poole - Too Cool Dubby Careless (JP009" -> "... (JP009)"
    if title.count("(") > title.count(")"):
        title += ")"

    return title


def normalise_title_edges(title: str) -> str:
    title = title.strip()

    # Remove leading broken dash:
    # "- Not Like Us Kendrick Lamar..." -> "Not Like Us Kendrick Lamar..."
    title = re.sub(r"^\s*-\s*", "", title)

    title = re.sub(r"^(?:\d{2,4}\s*-\s*){2,}", "", title)
    title = re.sub(r"^\d+\s*-\s*", "", title)

    title = re.sub(
        r"^(?=.*(?:\d{1,2}[AB]))(?:(?:\d{1,2}[AB]|\d{1,3})\s*-\s*)+",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"(?:\s*-\s*(?:\d{1,2}[AB]|\d{1,3}))+$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s+\d{1,2}[AB]\s+\d{2,3}$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s+\d{2,3}\s*bpm$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    if re.search(r"\bintro\b", title, flags=re.IGNORECASE):
        title = re.sub(r"\s+\d{2,3}$", "", title)

    return title.strip()


def normalise_no_intro(title: str) -> str:
    title = re.sub(
        r"\s*\(\s*no\s+intro\s*\)",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s*\bno\s+intro\b",
        "",
        title,
        flags=re.IGNORECASE,
    )

    return normalise_whitespace(title)


def normalise_intro_versions(title: str) -> str:
    title = title.strip()

    if not re.search(r"\bintro\b", title, flags=re.IGNORECASE):
        return title

    clean_dirty = extract_clean_dirty(title)
    intro_blocks = extract_intro_blocks(title)

    pool_name = None

    for block in intro_blocks:
        candidate = extract_pool_name_from_intro_block(block)
        if candidate:
            pool_name = candidate

    title = remove_intro_blocks(title)

    loose_pool = extract_loose_intro_pool(title)

    if loose_pool:
        pool_name = loose_pool
        title = remove_loose_intro_phrase(title)
    else:
        # Generic loose ending:
        # "Party Rock Anthem - intro" -> "Party Rock Anthem"
        # "Party Rock Anthem Intro" -> "Party Rock Anthem"
        title = remove_generic_loose_intro(title)

    title = remove_clean_dirty_tags(title)
    title = normalise_whitespace(title)

    if not title:
        return ""

    if pool_name and clean_dirty:
        return f"{title} ({pool_name} Intro) ({clean_dirty})"

    if pool_name:
        return f"{title} ({pool_name} Intro)"

    if clean_dirty:
        return f"{title} (Intro) ({clean_dirty})"

    return f"{title} (Intro)"

def remove_generic_loose_intro(title: str) -> str:
    title = re.sub(
        r"\s*-\s*intro\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s+\bintro\b\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    return title.strip()

def extract_clean_dirty( title: str) -> str | None:
        if re.search(r"\bclean\b", title, flags=re.IGNORECASE):
            return "Clean"

        if re.search(r"\bdirty\b", title, flags=re.IGNORECASE):
            return "Dirty"

        if re.search(r"\bexplicit\b", title, flags=re.IGNORECASE):
            return "Dirty"

        return None


def extract_intro_blocks( title: str) -> list[str]:
        return re.findall(
            r"\(([^)]*\bintro\b[^)]*)\)",
            title,
            flags=re.IGNORECASE,
        )


def extract_pool_name_from_intro_block(block: str) -> str | None:
    candidate = re.sub(
        r"\b(intro|edit|clean|dirty|short|outro|throwback|urban|uk|hype|epic|flat|chorus|bar|acap|acapella)\b",
        "",
        block,
        flags=re.IGNORECASE,
    )

    # Remove leftover separators
    candidate = re.sub(r"[-–—_/]+", " ", candidate)

    candidate = normalise_whitespace(candidate)

    # If no letters/numbers remain, it was just "Intro - Clean" or "Intro / Clean"
    if not re.search(r"[A-Za-z0-9]", candidate):
        return None

    return format_pool_name(candidate)


def remove_intro_blocks( title: str) -> str:
        return re.sub(
            r"\s*\([^)]*\bintro\b[^)]*\)",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()


def extract_loose_intro_pool( title: str) -> str | None:
        """
        Finds pool names in loose phrases like:
            Water (Remix) CK Intro - Dirty
            Gun Lean - Club Hack Hype Intro (Dirty)
            One Dance - Jordan Crisp Acap Intro
        """
        match = re.search(
            r"(?:^|\s-\s|\s)([A-Za-z][A-Za-z0-9 '&.-]*(?:\s+[A-Za-z][A-Za-z0-9 '&.-]*){0,4})\s+\bintro\b",
            title,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        candidate = match.group(1).strip()

        candidate = re.sub(
            r"\b(clean|dirty|explicit|edit|hype|epic|flat|chorus|bar|acap|acapella)\b",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = normalise_whitespace(candidate)

        if not candidate:
            return None

        return format_pool_name(candidate)


def remove_loose_intro_phrase( title: str) -> str:
        """
        Removes loose intro wording, but keeps the actual song title.

        Examples:
            "Water (Remix) CK Intro - Dirty"
            -> "Water (Remix)"

            "Gun Lean - Club Hack Hype Intro (Dirty)"
            -> "Gun Lean"
        """
        title = re.sub(
            r"\s*-\s*[A-Za-z][A-Za-z0-9 '&.-]*(?:\s+[A-Za-z][A-Za-z0-9 '&.-]*){0,5}\s+\bintro\b.*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\s+[A-Za-z][A-Za-z0-9 '&.-]*(?:\s+[A-Za-z][A-Za-z0-9 '&.-]*){0,5}\s+\bintro\b.*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

        return title.strip()


def remove_clean_dirty_tags( title: str) -> str:
        title = re.sub(
            r"\s*\(\s*(clean|dirty|explicit)\s*\)",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\s*\b(clean|dirty|explicit)\b\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

        return title.strip()


def normalise_whitespace( title: str) -> str:
        title = re.sub(r"\s+", " ", title)
        title = re.sub(r"\s+-\s+", " - ", title)
        return title.strip()


def format_pool_name( pool_name: str) -> str:
        known = {
            "ck": "CK",
            "hh": "HH",
            "tmu": "TMU",
            "mmp": "MMP",
            "djcity": "DJcity",
            "cflo": "CFLO",
        }

        words = pool_name.split()
        formatted = []

        for word in words:
            key = word.lower()
            if key in known:
                formatted.append(known[key])
            elif key == "dj":
                formatted.append("DJ")
            else:
                formatted.append(word[:1].upper() + word[1:].lower())

        return " ".join(formatted)
