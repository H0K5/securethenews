# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-28 23:22
# http://docs.wagtail.io/en/v1.6.3/topics/streamfield.html#migrating-richtextfields-to-streamfield
from __future__ import unicode_literals

from django.db import migrations
from wagtail.wagtailcore.rich_text import RichText


def convert_to_streamfield(apps, schema_editor):
    ContentPage = apps.get_model('home', 'ContentPage')
    for page in ContentPage.objects.all():
        # That page.body could be "false-y" yet have a raw_text attribute seems
        # weird; this is an intentional design choice by Wagtail meant to
        # simplify migrations from RichTextField to StreamField.
        if page.body.raw_text and not page.body:
            page.body = [
                ('rich_text', RichText(page.body.raw_text)),
            ]
            page.save()


def convert_to_richtext(apps, schema_editor):
    ContentPage = apps.get_model('home', 'ContentPage')
    for page in ContentPage.objects.all():
        if page.body.raw_text is None:
            raw_text = ''.join([
                child.value.source for child in page.body
                if child.block_type == 'rich_text'
            ])
            page.body = raw_text
            page.save()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0007_auto_20160930_1701'),
    ]

    operations = [
        migrations.RunPython(
            convert_to_streamfield,
            convert_to_richtext,
        ),
    ]
