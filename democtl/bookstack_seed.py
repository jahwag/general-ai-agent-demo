from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .bookstack import BookStackClient, BookStackConfig


READER_ROLE = "Cora Knowledge Reader"
READER_EMAIL = "cora.knowledge@example.invalid"
READER_PERMISSIONS = [
    "access-api",
    "bookshelf-view-all",
    "book-view-all",
    "chapter-view-all",
    "page-view-all",
    "revision-view-all",
]


def _data_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise ValueError(f"BookStack {label} response did not contain a data list")
    return [item for item in value["data"] if isinstance(item, dict)]


def _find(items: list[dict[str, Any]], field: str, value: object) -> dict[str, Any] | None:
    return next((item for item in items if item.get(field) == value), None)


def _tag_pairs(value: object) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        return []
    pairs = [
        (str(item.get("name", "")), str(item.get("value", "")))
        for item in value
        if isinstance(item, dict)
    ]
    return sorted(pairs)


def _page_matches(
    current: dict[str, Any], markdown: str, tags: list[dict[str, str]]
) -> bool:
    current_markdown = current.get("markdown")
    return (
        isinstance(current_markdown, str)
        and current_markdown.rstrip() == markdown.rstrip()
        and _tag_pairs(current.get("tags")) == _tag_pairs(tags)
    )


def _governed_markdown(content: str, governance: dict[str, Any]) -> str:
    body = content.strip()
    if body.startswith("# "):
        body = "\n".join(body.splitlines()[1:]).lstrip()
    return (
        "> **Approved synthetic demo article**  \n"
        f"> **Owner:** {governance['owner']}  \n"
        f"> **Status:** {governance['status']}  \n"
        f"> **Review due:** {governance['review_due']}  \n"
        f"> **Classification:** {governance['classification']}\n\n"
        f"{body}\n"
    )


def seed(
    client: BookStackClient,
    manifest_path: Path,
    kb_dir: Path,
    admin_password_file: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("BookStack manifest must be an object")
    admin_password = admin_password_file.read_text(encoding="utf-8").strip()
    if len(admin_password) < 12:
        raise ValueError("BookStack demo operator password file is invalid")

    client._request(
        "PUT",
        "/api/users/1",
        {
            "name": "Demo Knowledge Owner",
            "email": "demo.knowledge.owner@example.invalid",
            "password": admin_password,
        },
    )

    roles = _data_list(client._request("GET", "/api/roles?count=100"), "roles")
    role = _find(roles, "display_name", READER_ROLE)
    role_body = {
        "display_name": READER_ROLE,
        "description": "Read-only API access to approved demo knowledge for Cora.",
        "permissions": READER_PERMISSIONS,
    }
    if role is None:
        role = client._request("POST", "/api/roles", role_body)
    else:
        role = client._request("PUT", f"/api/roles/{role['id']}", role_body)
    if not isinstance(role, dict) or not isinstance(role.get("id"), int):
        raise ValueError("BookStack reader role was not created")

    users = _data_list(client._request("GET", "/api/users?count=100"), "users")
    reader = _find(users, "email", READER_EMAIL)
    reader_body = {
        "name": "Cora AI",
        "email": READER_EMAIL,
        "roles": [role["id"]],
    }
    if reader is None:
        reader = client._request("POST", "/api/users", reader_body)
    else:
        reader = client._request("PUT", f"/api/users/{reader['id']}", reader_body)
    if not isinstance(reader, dict) or not isinstance(reader.get("id"), int):
        raise ValueError("BookStack Cora user was not created")

    book_spec = manifest.get("book")
    governance = manifest.get("governance")
    articles = manifest.get("articles")
    if not isinstance(book_spec, dict) or not isinstance(governance, dict):
        raise ValueError("BookStack manifest book and governance must be objects")
    if not isinstance(articles, list) or not articles:
        raise ValueError("BookStack manifest articles must be a non-empty list")

    books = _data_list(client._request("GET", "/api/books?count=100"), "books")
    book = _find(books, "name", book_spec.get("name"))
    if book is None:
        book = client._request("POST", "/api/books", book_spec)
    else:
        book = client._request("PUT", f"/api/books/{book['id']}", book_spec)
    if not isinstance(book, dict) or not isinstance(book.get("id"), int):
        raise ValueError("BookStack demo book was not created")

    pages = _data_list(client._request("GET", "/api/pages?count=100"), "pages")
    seeded_pages: list[dict[str, Any]] = []
    for article in articles:
        if not isinstance(article, dict):
            raise ValueError("BookStack article specification must be an object")
        source_name = article.get("source")
        title = article.get("title")
        category = article.get("category")
        if not all(isinstance(value, str) and value for value in (source_name, title, category)):
            raise ValueError("BookStack article source, title, and category are required")
        source_path = kb_dir / source_name
        if source_path.parent.resolve() != kb_dir.resolve() or not source_path.is_file():
            raise ValueError(f"unsafe or missing knowledge source: {source_name}")
        markdown = _governed_markdown(
            source_path.read_text(encoding="utf-8"), governance
        )
        tags = [
            {"name": "Status", "value": governance["status"]},
            {"name": "Owner", "value": governance["owner"]},
            {"name": "Review due", "value": governance["review_due"]},
            {"name": "Classification", "value": governance["classification"]},
            {"name": "Category", "value": category},
            {"name": "Synthetic demo", "value": "Yes"},
        ]
        page = next(
            (
                item
                for item in pages
                if item.get("book_id") == book["id"] and item.get("name") == title
            ),
            None,
        )
        page_body = {
            "book_id": book["id"],
            "name": title,
            "markdown": markdown,
            "tags": tags,
        }
        if page is None:
            page = client._request("POST", "/api/pages", page_body)
        else:
            current = client.get_page(page["id"])
            if not _page_matches(current, markdown, tags):
                page = client._request("PUT", f"/api/pages/{page['id']}", page_body)
            else:
                page = current
        if not isinstance(page, dict) or not isinstance(page.get("id"), int):
            raise ValueError(f"BookStack page was not created: {title}")
        seeded_pages.append(
            {
                "id": page["id"],
                "title": title,
                "revision": page.get("revision_count"),
                "url": f"{client.config.base_url}/link/{page['id']}",
            }
        )

    return {
        "book_id": book["id"],
        "book_name": book_spec["name"],
        "reader_user_id": reader["id"],
        "reader_role": READER_ROLE,
        "pages": seeded_pages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="gaidemo-bookstack-seed")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--kb-dir", type=Path, required=True)
    parser.add_argument("--admin-password-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = seed(
        BookStackClient(BookStackConfig.from_environment()),
        args.manifest,
        args.kb_dir,
        args.admin_password_file,
    )
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
