from django import forms
from django.contrib import admin
from ckeditor.widgets import CKEditorWidget

from ecolex.models import StaticContent


class StaticContentForm(forms.ModelForm):
    body_en = forms.CharField(widget=CKEditorWidget())
    body_es = forms.CharField(widget=CKEditorWidget())
    body_fr = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = StaticContent
        fields = ['name', 'body_en', 'body_es', 'body_fr']


class StaticContentAdmin(admin.ModelAdmin):
    form = StaticContentForm

admin.site.register(StaticContent, StaticContentAdmin)
