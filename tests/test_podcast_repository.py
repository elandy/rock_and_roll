from app.db.models import Podcast
from app.repositories.podcasts import list_podcasts


def add_podcast(
    db,
    *,
    title: str,
    author: str | None = "Author",
    description: str | None = "Description",
    category: str | None = "Rock",
    country: str | None = "USA",
):
    podcast = Podcast(
        source="test",
        source_id=title.lower().replace(" ", "-"),
        title=title,
        author=author,
        description=description,
        category=category,
        country=country,
        genres=[],
        color_palette=[],
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return podcast


def test_list_podcasts_paginates_at_database_level(db):
    for title in ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]:
        add_podcast(db, title=title)

    items, total = list_podcasts(
        db,
        page=2,
        page_size=2,
    )

    assert total == 5
    assert [item.title for item in items] == ["Charlie", "Delta"]


def test_list_podcasts_searches_title(db):
    add_podcast(db, title="Rock Weekly")
    add_podcast(db, title="Jazz Hour")

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        search="rock",
    )

    assert total == 1
    assert [item.title for item in items] == ["Rock Weekly"]


def test_list_podcasts_searches_author(db):
    add_podcast(
        db,
        title="Podcast One",
        author="Rock Collective",
    )
    add_podcast(
        db,
        title="Podcast Two",
        author="Jazz Collective",
    )

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        search="rock collective",
    )

    assert total == 1
    assert items[0].title == "Podcast One"


def test_list_podcasts_searches_description(db):
    add_podcast(
        db,
        title="Podcast One",
        description="Interviews with legendary guitarists.",
    )
    add_podcast(
        db,
        title="Podcast Two",
        description="Electronic music news.",
    )

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        search="guitarists",
    )

    assert total == 1
    assert items[0].title == "Podcast One"


def test_list_podcasts_filters_by_category(db):
    add_podcast(
        db,
        title="Rock Show",
        category="Rock",
    )
    add_podcast(
        db,
        title="Jazz Show",
        category="Jazz",
    )

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        category="rock",
    )

    assert total == 1
    assert items[0].title == "Rock Show"


def test_list_podcasts_filters_by_country(db):
    add_podcast(
        db,
        title="US Show",
        country="USA",
    )
    add_podcast(
        db,
        title="UK Show",
        country="UK",
    )

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        country="usa",
    )

    assert total == 1
    assert items[0].title == "US Show"


def test_list_podcasts_combines_filters(db):
    add_podcast(
        db,
        title="US Rock",
        category="Rock",
        country="USA",
    )
    add_podcast(
        db,
        title="UK Rock",
        category="Rock",
        country="UK",
    )
    add_podcast(
        db,
        title="US Jazz",
        category="Jazz",
        country="USA",
    )

    items, total = list_podcasts(
        db,
        page=1,
        page_size=20,
        category="rock",
        country="usa",
    )

    assert total == 1
    assert items[0].title == "US Rock"


def test_list_podcasts_returns_empty_page(db):
    add_podcast(db, title="Only Podcast")

    items, total = list_podcasts(
        db,
        page=2,
        page_size=20,
    )

    assert total == 1
    assert items == []