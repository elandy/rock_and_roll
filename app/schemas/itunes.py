from pydantic import BaseModel, ConfigDict, Field


class ITunesPodcast(BaseModel):
    model_config = ConfigDict(extra="ignore")

    collection_id: int = Field(
        alias="collectionId",
        gt=0,
    )

    artist_name: str | None = Field(
        default=None,
        alias="artistName",
    )

    collection_name: str | None = Field(
        default=None,
        alias="collectionName",
    )

    feed_url: str | None = Field(
        default=None,
        alias="feedUrl",
    )

    collection_view_url: str | None = Field(
        default=None,
        alias="collectionViewUrl",
    )

    artwork_url600: str | None = Field(
        default=None,
        alias="artworkUrl600",
    )

    artwork_url100: str | None = Field(
        default=None,
        alias="artworkUrl100",
    )

    primary_genre_name: str | None = Field(
        default=None,
        alias="primaryGenreName",
    )

    genres: list[str] = Field(default_factory=list)

    country: str | None = None

    release_date: str | None = Field(
        default=None,
        alias="releaseDate",
    )


class ITunesSearchResponse(BaseModel):
    result_count: int = Field(alias="resultCount")

    results: list[ITunesPodcast] = Field(
        default_factory=list,
    )