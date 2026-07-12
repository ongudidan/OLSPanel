from django.db import models

class UserSettings(models.Model):
    font_size = models.CharField(max_length=50, null=True, db_index=True)
    hide_hiden_file = models.IntegerField(default=1)
    hide_folder_size = models.IntegerField(default=1)
    two_step = models.IntegerField(default=0)
    api = models.IntegerField(default=0)
    userid = models.IntegerField(null=True, blank=True)
    maximum_backup = models.IntegerField(default=100)
    secret = models.CharField(max_length=255, null=True)
    hour_maximum_backup = models.IntegerField(default=24)
    day_maximum_backup = models.IntegerField(default=100)
    week_maximum_backup = models.IntegerField(default=50)
    month_maximum_backup = models.IntegerField(default=12)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return self.name
# Create your models here.
