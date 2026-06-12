from django.apps import AppConfig

class StatistikaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'statistika'

    def ready(self):
        import statistika.signals