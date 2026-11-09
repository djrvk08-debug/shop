"""Catalog search service using an inverted index for keyword search and a trie for autocomplete."""
import re
from decimal import Decimal
from urllib.parse import urlsplit

from extensions import db
from models import Product


class AutocompleteTrieNode:
    """Node structure for Trie-based prefix autocomplete."""

    def __init__(self):
        self.children: dict[str, AutocompleteTrieNode] = {}
        self.is_terminal: bool = False
        self.words: list[str] = []


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def build_inverted_index() -> dict[str, set[int]]:
    """Build an in-memory inverted index mapping normalized tokens to product IDs.

    :return: Dictionary mapping word tokens to set of product IDs.
    """
    index: dict[str, set[int]] = {}
    for product in Product.query.all():
        for token in set(_tokens(product.name + " " + product.pack_size)):
            index.setdefault(token, set()).add(product.id)
    return index


def search_catalog(query: str) -> list[int]:
    """Execute keyword search against the catalog inverted index.

    :param query: Raw user search string.
    :return: List of matching product IDs ranked by relevance.
    """
    terms = list(dict.fromkeys(_tokens(query)))
    if not terms:
        return []
    index = build_inverted_index()
    scores: dict[int, int] = {}
    for term in terms:
        for product_id in index.get(term, set()):
            scores[product_id] = scores.get(product_id, 0) + 1
    return sorted(scores, key=lambda product_id: (-scores[product_id], product_id))


def build_trie() -> AutocompleteTrieNode:
    """Build a prefix Trie populated with catalog product titles.

    :return: Root AutocompleteTrieNode of the constructed trie.
    """
    root = AutocompleteTrieNode()
    titles = [product.name for product in Product.query.order_by(Product.name).all()]
    for title in titles:
        for token in set(_tokens(title)):
            node = root
            for character in token:
                node = node.children.setdefault(character, AutocompleteTrieNode())
                if title not in node.words:
                    node.words.append(title)
            node.is_terminal = True
    return root


def autocomplete_query(prefix: str, limit: int = 5) -> list[str]:
    """Provide autocomplete suggestions for a given search prefix using the Trie.

    :param prefix: Partial query prefix typed by user.
    :param limit: Maximum number of suggestions to return.
    :return: List of completion suggestions.
    """
    if not isinstance(limit, int) or limit <= 0:
        return []
    node = build_trie()
    for character in prefix.strip().casefold():
        node = node.children.get(character)
        if node is None:
            return []
    return sorted(node.words, key=str.casefold)[:limit]


def get_product(product_id: int) -> Product | None:
    return db.session.get(Product, product_id)


def list_products(page: int = 1, per_page: int = 12, sort: str = "name"):
    query = Product.query
    sort_columns = {
        "name": Product.name.asc(),
        "price": Product.price.asc(),
        "-price": Product.price.desc(),
    }
    return query.order_by(sort_columns.get(sort, Product.name.asc())).paginate(
        page=max(page, 1), per_page=min(max(per_page, 1), 100), error_out=False
    )


def products_by_ids(product_ids: list[int]) -> list[Product]:
    if not product_ids:
        return []
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    by_id = {product.id: product for product in products}
    return [by_id[product_id] for product_id in product_ids if product_id in by_id]


def seed_sample_data() -> None:
    """Insert the demo catalog once, preserving records already managed by staff."""
    samples = [
        ("Pearl Oyster Mushrooms", 120, "200g", 42),
        ("White Button Mushrooms", 75, "200g", 80),
        ("Fresh Shiitake Mushrooms", 210, "200g", 6),
        ("Royal King Oyster", 190, "200g", 18),
        ("Pristine Milky Mushrooms", 95, "200g", 28),
        ("Sun-Dried Shiitake & Porcini Mix", 299, "100g", 50),
        ("Wild Mushroom Umami Powder", 240, "100g", 65),
        ("Flamingo Pink Oyster", 180, "200g", 0),
    ]
    for name, price, pack_size, stock in samples:
        if Product.query.filter_by(name=name).first() is None:
            db.session.add(Product(name=name, price=Decimal(price), pack_size=pack_size, stock=stock))
    db.session.commit()


def create_product(name: str, price: Decimal, pack_size: str, stock: int,
                   thumbnail_url: str | None = None) -> Product:
    name = name.strip() if isinstance(name, str) else ""
    if not name or len(name) > 255:
        raise ValueError("Product name must contain 1 to 255 characters.")
    try:
        price = Decimal(str(price))
        stock = int(stock)
    except (ValueError, TypeError):
        raise ValueError("Price, pack size, and stock must be valid values.")
    pack_size = pack_size.strip() if isinstance(pack_size, str) else ""
    if not pack_size or len(pack_size) > 50:
        raise ValueError("Pack size is required (for example, 100g).")
    if not price.is_finite() or price <= 0 or stock < 0:
        raise ValueError("Price must be positive and stock cannot be negative.")
    thumbnail_url = thumbnail_url.strip() if isinstance(thumbnail_url, str) else ""
    if thumbnail_url:
        try:
            parsed_url = urlsplit(thumbnail_url)
        except ValueError as error:
            raise ValueError("Thumbnail must be a valid HTTP or HTTPS URL.") from error
        if (len(thumbnail_url) > 2048 or parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc or parsed_url.username or parsed_url.password):
            raise ValueError("Thumbnail must be a valid HTTP or HTTPS URL.")
    else:
        thumbnail_url = None
    product = Product(name=name, price=price, pack_size=pack_size, stock=stock,
                      thumbnail_url=thumbnail_url)
    db.session.add(product)
    db.session.commit()
    return product
