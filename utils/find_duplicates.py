from models.models import Song, SongQueueItem, InternalPlaylist
from rekordbox.rekordbox import Rekordbox

import re


VERSION_WORDS = {
    "intro",
    "clean",
    "dirty",
    "extended",
    "edit",
    "radio",
    "single",
    "version",
    "remaster",
    "remastered",
    "original",
    "mix",
    "explicit",
}


def has_word(text: str | None, word: str) -> bool:
    if not text:
        return False

    pattern = rf"\b{re.escape(word.lower())}\b"
    return bool(re.search(pattern, text.lower()))


async def build_queue(playlist: InternalPlaylist):
    rb = Rekordbox()
    await rb.start_rekordbox_connection()

    queue: list[SongQueueItem] = []

    for song in playlist.songs:
        item = await create_song_queue_item(song, rb)
        queue.append(item)

    print(queue)
    return queue

def title_similarity(source_title: str, result_title: str) -> float:
    source_words = set(source_title.split())
    result_words = set(result_title.split())

    if not source_words or not result_words:
        return 0

    overlap = len(source_words & result_words)
    shorter_len = min(len(source_words), len(result_words))
    longer_len = max(len(source_words), len(result_words))

    coverage_of_shorter = overlap / shorter_len
    coverage_of_longer = overlap / longer_len

    # both titles share the important core words,
    # but one may have remix/subtitle noise
    return (coverage_of_shorter * 0.7) + (coverage_of_longer * 0.3)

async def create_song_queue_item(song: Song, rb: Rekordbox):
    song_queue_item = SongQueueItem(song, False, False, False, False, False)

    matched_results = []

    for title_query, artist_query in get_search_queries(song):
        print(f"\nSEARCH: {title_query} | artist={artist_query}")

        search_results = await rb.search_tracks(title_query, artist_query)
        for r in search_results:
            print("RAW:", getattr(r, "title", None), "|", getattr(r, "artist", None))
    
        matches = [
            result for result in search_results
            if is_same_song(song, result)
        ]

        matched_results.extend(matches)

        if matches:
            break

    for result in dedupe_results(matched_results):
        print(result.title)

        song_version = get_song_version(result.title)

        match song_version:
            case "clean_intro":
                song_queue_item.clean_intro = True
            case "clean":
                song_queue_item.clean = True
            case "normal":
                song_queue_item.normal = True
            case "intro":
                song_queue_item.intro = True
            case "extended":
                song_queue_item.extended = True

    print(song_queue_item)
    return song_queue_item


def get_search_queries(song: Song) -> list[tuple[str | None, str | None]]:
    title = song.title
    artist = song.artist

    queries: list[tuple[str, str | None]] = [
        (search_clean_title(title), None),
        (search_core_title(title), None),
        (remove_mix_suffix(search_core_title(title)), None),

        (search_clean_title(title), artist),
        (search_core_title(title), artist),
        (remove_mix_suffix(search_core_title(title)), artist),

        # final broad fallback
        (None, artist),
    ]


    seen = set()
    unique: list[tuple[str, str | None]] = []

    for q_title, q_artist in queries:
        q_title = q_title.strip() if q_title else None
        q_artist = q_artist.strip() if q_artist else None

        if not q_title and not q_artist:
            continue

        key = (
                q_title.lower() if q_title else None,
                q_artist.lower() if q_artist else None,
            )
        if key in seen:
            continue

        seen.add(key)
        unique.append((q_title, q_artist))

    return unique

def remove_mix_suffix(title: str | None) -> str:
    if not title:
        return ""

    title = re.sub(r"\bextended\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bclub\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bbasement\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bstrip\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bremix\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bmix\b.*$", " ", title, flags=re.IGNORECASE)

    title = re.sub(r"\s+", " ", title)
    return title.strip()

def clean_title(title: str | None) -> str:
    if not title:
        return ""

    title = title.lower()

    title = re.sub(r"\b\d{4}\b", " ", title)
    title = re.sub(r"\bremaster(?:ed)?\b", " ", title)
    title = re.sub(r"\bradio edit\b", " ", title)
    title = re.sub(r"\bsingle version\b", " ", title)
    title = re.sub(r"\balbum version\b", " ", title)
    title = re.sub(r"\boriginal mix\b", " ", title)
    title = re.sub(r"\bclassic radio\b", " ", title)
    title = re.sub(r"\bfrom .* soundtrack\b", " ", title)

    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def core_title(title: str | None) -> str:
    title = clean_title(title)

    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\[[^]]*\]", " ", title)

    title = re.sub(r"\bwith\b.*$", " ", title)
    title = re.sub(r"\bfeat\b.*$", " ", title)
    title = re.sub(r"\bft\b.*$", " ", title)
    title = re.sub(r"\bfeaturing\b.*$", " ", title)

    title = re.sub(r"\s+", " ", title)

    return title.strip()


def remove_brackets(title: str | None) -> str:
    if not title:
        return ""

    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\[[^]]*\]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def normalise_title(title: str | None) -> str:
    title = clean_title(title)

    title = re.sub(
        r"\(([^)]*(intro|clean|dirty|extended|edit|radio|single|version|remaster|remastered|original mix|album version)[^)]*)\)",
        " ",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\[([^]]*(intro|clean|dirty|extended|edit|radio|single|version|remaster|remastered|original mix|album version)[^]]*)\]",
        " ",
        title,
        flags=re.IGNORECASE,
    )

    words = [
        word for word in title.split()
        if word not in VERSION_WORDS
    ]

    return " ".join(words).strip()


def normalise_artist(artist: str | None) -> str:
    if not artist:
        return ""

    artist = artist.lower()

    artist = re.sub(r"[^a-z0-9\s]", " ", artist)

    words_to_remove = {
        "feat",
        "ft",
        "featuring",
        "with",
        "and",
        "the",
    }

    words = [
        word for word in artist.split()
        if word not in words_to_remove
    ]

    return " ".join(words).strip()


def is_same_song(source: Song, result) -> bool:
    source_title = normalise_title(source.title)
    result_title = normalise_title(getattr(result, "title", None))

    if not source_title or not result_title:
        return False

    if source_title == result_title:
        return True

    source_words = set(source_title.split())
    result_words = set(result_title.split())

    if not source_words or not result_words:
        return False

    source_artist = normalise_artist(source.artist)
    result_artist = normalise_artist(getattr(result, "artist", None))

    artist_matches = (
        source_artist
        and result_artist
        and (
            source_artist in result_artist
            or result_artist in source_artist
        )
    )

    artist_conflict = (
        source_artist
        and result_artist
        and not artist_matches
    )
    
    if artist_conflict:
        return False
    
    similarity = title_similarity(source_title, result_title)

    if artist_matches and similarity >= 0.55:
        return True

    if not result_artist and similarity >= 0.75:
        return True

    if source_words.issubset(result_words):
        extra_words = result_words - source_words

        if artist_matches and len(extra_words) <= 4:
            return True

        if not result_artist and len(extra_words) <= 1:
            return True

    overlap = len(source_words & result_words)
    overlap_ratio = overlap / len(source_words)

    if artist_matches and overlap_ratio >= 0.75:
        return True

    return False


def get_song_version(title: str | None) -> str:
    has_intro = has_word(title, "intro")
    has_clean = has_word(title, "clean")
    has_extended = has_word(title, "extended")
    has_edit = has_word(title, "edit")
    has_remix = has_word(title, "remix")
    has_bootleg = has_word(title, "bootleg")

    if has_intro and has_clean:
        return "clean_intro"

    if has_intro:
        return "intro"

    if has_clean:
        return "clean"

    if has_extended:
        return "extended"

    if has_remix or has_bootleg:
        return "normal"

    if has_edit:
        return "normal"

    return "normal"


def dedupe_results(results):
    seen = set()
    unique = []

    for result in results:
        key = (
            normalise_title(getattr(result, "title", None)),
            normalise_artist(getattr(result, "artist", None)),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(result)

    return unique

def search_clean_title(title: str | None) -> str:
    if not title:
        return ""

    title = title.strip()

    # remove version text, but keep punctuation like ! ? ' &
    title = re.sub(r"\b\d{4}\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bremaster(?:ed)?\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bradio edit\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bsingle version\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\balbum version\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\boriginal mix\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bclassic radio\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bfrom .* soundtrack\b", " ", title, flags=re.IGNORECASE)

    # keep useful punctuation, remove only separators that usually hurt
    title = re.sub(r"[-_/]+", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def search_core_title(title: str | None) -> str:
    title = search_clean_title(title)

    # for search fallback, remove bracketed suffixes
    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"\[[^]]*\]", " ", title)

    title = re.sub(r"\bwith\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bfeat\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bft\b.*$", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\bfeaturing\b.*$", " ", title, flags=re.IGNORECASE)

    title = re.sub(r"\s+", " ", title)

    return title.strip()