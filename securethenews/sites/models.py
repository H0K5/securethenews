from django.db import models
from django.utils.text import slugify


class Site(models.Model):
    name = models.CharField('Name', max_length=255, unique=True)
    slug = models.SlugField('Slug', unique=True, editable=False)

    domain = models.CharField(
        'Domain Name',
        max_length=255,
        unique=True,
        help_text='Specify the domain name without the scheme, e.g. "example.com" instead of "https://example.com"')

    added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Site, self).save(*args, **kwargs)

    def to_dict(self):
        # TODO figure out the best way to optimize this
        scan = self.scans.latest()

        return dict(
            domain=self.domain,
            name=self.name,
            slug=self.slug,
            live=scan.live,
            valid_https=scan.valid_https,
            default_https=scan.defaults_to_https,
            enforces_https=scan.strictly_forces_https,
            downgrades_https=scan.downgrades_https,
            score=scan.score,
        )

class Scan(models.Model):
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='scans')

    timestamp = models.DateTimeField(auto_now_add=True)

    # Scan results
    # TODO: If a site isn't live, there may not be much of a point storing the
    # scan. This requirement also increases the complexity of the data model
    # since it means the attributes of the scan results must be nullable.
    live = models.BooleanField()

    # These are nullable because it may not be possible to determine their
    # values (for example, if the site is down at the time of the scan).
    valid_https = models.NullBooleanField()
    downgrades_https = models.NullBooleanField()
    defaults_to_https = models.NullBooleanField()
    strictly_forces_https = models.NullBooleanField()

    hsts = models.NullBooleanField()
    hsts_max_age = models.IntegerField(null=True)
    hsts_entire_domain = models.NullBooleanField()
    hsts_preload_ready = models.NullBooleanField()
    hsts_preloaded = models.NullBooleanField()

    score = models.IntegerField(default=0, editable=False)

    # To aid debugging, we store the full stdout and stderr from pshtt.
    pshtt_stdout = models.TextField()
    pshtt_stderr = models.TextField()

    class Meta:
        get_latest_by = 'timestamp'

    def __str__(self):
        return "{} from {:%Y-%m-%d %H:%M}".format(self.site.name,
                                                  self.timestamp)

    def save(self, *args, **kwargs):
        self._score()
        super(Scan, self).save(*args, **kwargs)

    def _score(self):
        """Compute a score between 0-100 for the quality of the HTTPS implementation observed by this scan."""
        # TODO: this is a very basic metric, just so we have something for
        # testing. Revisit.
        score = 0
        if self.valid_https:
            if self.downgrades_https:
                score = 30
            if self.defaults_to_https:
                score = 50
            if self.strictly_forces_https:
                score = 70

                if self.hsts:
                    score += 5

                # HSTS max-age is specified in seconds
                eighteen_weeks = 18*7*24*60*60
                if self.hsts_max_age and self.hsts_max_age >= eighteen_weeks:
                    score += 5

                if self.hsts_entire_domain:
                    score += 10
                if self.hsts_preload_ready:
                    score += 5
                if self.hsts_preloaded:
                    score += 5

        assert 0 <= score <= 100, \
            "score must be between 0 and 100 (inclusive), is: {}".format(score)
        self.score = score
