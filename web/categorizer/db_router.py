VECTORS_DB = "vectors"
VECTORS_APP = "categorizer"


class VectorRouter:
    """Route the categorizer app's models and migrations to the pgvector DB."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == VECTORS_APP:
            return VECTORS_DB
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == VECTORS_APP:
            return VECTORS_DB
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == VECTORS_DB:
            return app_label == VECTORS_APP
        if app_label == VECTORS_APP:
            return False
        return None
