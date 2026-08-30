# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Extending User Model Using a One-To-One Link
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
   
    
    

    def __str__(self):
        return self.user.username

    

class Domain(models.Model):
    domain = models.CharField(max_length=255)
    userid = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userid')  # Use userid as the column name
    path = models.CharField(max_length=255)
    php = models.CharField(max_length=255)
    ssl_exp = models.CharField(max_length=255)
    line = models.CharField(max_length=255, null=True, blank=True, default='')

    class Meta:
        db_table = 'domain'  # Specify the database table name explicitly

    def __str__(self):
        return self.domain
        
        
        
class Dns_record(models.Model):
    name = models.CharField(max_length=255)
    domain_id = models.CharField(max_length=255)
    userid = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userid')  # Use userid as the column name
    type = models.CharField(max_length=255)
    content = models.CharField(max_length=255)
    ttl = models.CharField(max_length=255)
    prio = models.CharField(max_length=255)
    class Meta:
        db_table = 'records'  # Specify the database table name explicitly

    def __str__(self):
        return self.Dns_record 


class Package(models.Model):
    name = models.CharField(max_length=50, null=True, db_index=True)
    disk_space = models.IntegerField(default=0)
    bandwidth = models.IntegerField(default=0)
    email_accounts = models.IntegerField(default=0)
    databases = models.IntegerField(default=0)
    ftp_accounts = models.IntegerField(default=0)
    allowed_domains = models.IntegerField(default=0)
    userid = models.IntegerField(null=True, blank=True)
    enforce_disk_limits = models.BooleanField(default=False)
    allowed_subdomains = models.IntegerField(default=0)

    class Meta:
        db_table = 'packages'

    def __str__(self):
        return self.name
        
        
class Emails(models.Model):
    email = models.CharField(max_length=255)
    userid = models.CharField(max_length=255)
    mail = models.CharField(max_length=255)
    DiskUsage = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    domain_id = models.CharField(max_length=255)
    class Meta:
        db_table = 'email_users'  # Specify the database table name explicitly

    def __str__(self):
        return self.domain
        
class EmailForword(models.Model):
    source = models.CharField(max_length=255)
    userid = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    domain_id = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    class Meta:
        db_table = 'email_forwardings'  # Specify the database table name explicitly

    def __str__(self):
        return self.domain  


class Ftps(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.CharField(max_length=32)
    password = models.CharField(max_length=255)
    uid = models.IntegerField()
    gid = models.IntegerField()
    dir = models.CharField(max_length=255)
    QuotaSize = models.IntegerField()
    status = models.CharField(max_length=1)
    ULBandwidth = models.IntegerField()
    DLBandwidth = models.IntegerField()
    sate = models.DateField()
    LastModif = models.CharField(max_length=255)
    userid = models.IntegerField(null=True, blank=True)
    domain_id = models.IntegerField()
    class Meta:
        db_table = 'ftp'  # Specify the database table name explicitly

    def __str__(self):
        return self.domain    

class Bandwidth(models.Model):
    date = models.CharField(max_length=20, null=True, blank=True)  # Matches varchar(20)
    total = models.IntegerField(default=0)
    line = models.IntegerField(default=0)
    userid = models.IntegerField()
    class Meta:
        db_table = 'bandwidth'
        

    def __str__(self):
        return self.Bandwidth  




class BackupList(models.Model):
    # Fields based on the provided structure
    type = models.CharField(max_length=500, null=True, blank=True)
    userid = models.IntegerField()
    schedule = models.CharField(max_length=500, null=True, blank=True)
    path = models.CharField(max_length=500, null=True, blank=True)
    username = models.CharField(max_length=500, null=True, blank=True)
    host = models.CharField(max_length=500, null=True, blank=True)
    user = models.CharField(max_length=500, null=True, blank=True)
    password = models.CharField(max_length=500, null=True, blank=True)
    category = models.CharField(max_length=500, null=True, blank=True)
    user_access = models.IntegerField(default=0)

    # Meta information for database constraints or ordering
    class Meta:
        db_table = 'backup'  # Ensure this matches your table name
        

    def __str__(self):
        return self.BackupList  
        
         
        
class Timezone(models.Model):
    # Fields based on the provided structure
    timezone = models.CharField(max_length=500, null=True, blank=True)
    
    class Meta:
        db_table = 'timezone'  # Ensure this matches your table name
        
class AppSettings(models.Model):
    id = models.AutoField(primary_key=True)
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField(null=True, blank=True)
    type = models.CharField(
        max_length=10,
        choices=[
            ('string', 'string'),
            ('integer', 'integer'),
            ('boolean', 'boolean'),
            ('json', 'json'),
        ],
        default='string'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_settings'
        
        

class BlockedIP(models.Model):
    BLOCK_TYPE_CHOICES = [
        ("TEMP", "Temporary"),
        ("PERM", "Permanent"),
        ("NONE", "None"),  # Explicit no-block state
    ]

    ip_address = models.GenericIPAddressField(unique=True)
    block_type = models.CharField(
        max_length=10,  # Increased max_length for safety
        choices=BLOCK_TYPE_CHOICES,
        default="NONE",
    )
    first_detected = models.DateTimeField(auto_now_add=True)
    last_detected = models.DateTimeField(auto_now=True)
    attempts = models.IntegerField(default=0)
    temp_block_expires = models.DateTimeField(null=True, blank=True)
    temp_block_count = models.IntegerField(default=0)  # Count of temp blocks in 24h
    first_attempt_time = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=500)    

    class Meta:
        db_table = 'blocked_ip'

    def __str__(self):
        return f"{self.ip_address} - {self.block_type}"

    def is_temp_block_expired(self):
        return self.temp_block_expires and timezone.now() > self.temp_block_expires
        
        
class FilterBlockedIP(models.Model):
    BLOCK_TYPE_CHOICES = [
        ("TEMP", "Temporary"),
        ("PERM", "Permanent"),
        ("NONE", "None"),  # Explicit no-block state
    ]

    ip_address = models.GenericIPAddressField(unique=True)
    first_detected = models.DateTimeField(auto_now_add=True)
    last_detected = models.DateTimeField(auto_now=True)
    attempts = models.IntegerField(default=0)
    first_attempt_time = models.DateTimeField(null=True, blank=True)
    temp_block_count = models.IntegerField(default=0)  # Count of temp blocks in 24h
      

    class Meta:
        db_table = 'blocked_filter_ip'

    def __str__(self):
        return f"{self.ip_address} - {self.block_type}"

    def is_temp_block_expired(self):
        return self.temp_block_expires and timezone.now() > self.temp_block_expires         
        
        
class SSOToken(models.Model):
    user_id = models.IntegerField()  # External/WHMCS user ID
    token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sso_tokens'
        indexes = [
            models.Index(fields=['user_id']),
        ]                
        
        
        
class Apps(models.Model):
    userid = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    domain_id = models.IntegerField(null=True, blank=True)
    path = models.CharField(max_length=255, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    startup_file = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'apps'  # Specify the database table name explicitly

    def __str__(self):
        return self.apps            


class ApiKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=255, default='WHMCS')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'api_keys'

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class UserPasskey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passkeys')
    name = models.CharField(max_length=100, default="Security Key / Passkey")
    credential_id = models.CharField(max_length=255, unique=True, db_index=True)
    public_key = models.TextField()
    sign_count = models.IntegerField(default=0)
    aaguid = models.CharField(max_length=64, blank=True, null=True)
    transports = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_passkeys'

    def __str__(self):
        return f"{self.user.username} - {self.name}"