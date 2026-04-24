import logging
from datetime import timedelta

from concepts.models import Item
from django.db.utils import IntegrityError
from psycopg2.sql import SQL
from slurper.models import SlurperRun


class LmfdbSlurper:
    KNOWL_URL_PREFIX = "https://www.lmfdb.org/knowledge/show/"
    MIN_INTERVAL = timedelta(days=7)

    def __init__(self):
        self.source = Item.Source.LMFDB

    def fetch_rows(self):
        from lmf import db

        cur = db._execute(SQL("SELECT id, title, content FROM kwl_knowls"))
        columns = [desc[0] for desc in cur.description]
        for row in cur:
            yield dict(zip(columns, row))

    def row_to_item(self, row) -> Item:
        return Item(
            source=self.source,
            identifier=row["id"],
            url=self.KNOWL_URL_PREFIX + row["id"],
            name=row["title"],
            description=row["content"],
        )

    def save_items(self, force: bool = False):
        if not force and not SlurperRun.should_run(self.source, self.MIN_INTERVAL):
            logging.info(
                f"[{self.source.label}] skipped: ran less than "
                f"{self.MIN_INTERVAL.days} days ago (use --force to override)."
            )
            return
        total_saved = 0
        for row in self.fetch_rows():
            item = self.row_to_item(row)
            try:
                item.save()
                total_saved += 1
            except IntegrityError:
                logging.info(
                    f"Item {item.source} {item.identifier} is already in the database."
                )
        SlurperRun.mark_ran(self.source)
        logging.info(
            f"[{self.source.label}] save_items finished: {total_saved} items saved."
        )


LMFDB_SLURPER = LmfdbSlurper()
