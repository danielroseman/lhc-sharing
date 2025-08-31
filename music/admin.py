from direct_cloud_upload import CloudFileWidget, DdcuAdminMixin
from django import forms
from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from invitations.admin import InvitationAdmin
from invitations.models import Invitation
from music.models import DDCU_BUCKET_IDENTIFIER, Song


class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ["name", "slug", "created_at", "current", "files", "embed"]

        widgets = {
            "files": CloudFileWidget(
                bucket_identifier=DDCU_BUCKET_IDENTIFIER,
                path_prefix="media/",
                include_timestamp=False,
                allow_multiple=True,
            )
        }


@admin.register(Song)
class SongAdmin(DdcuAdminMixin):
    list_display = ("name", "current")
    list_editable = ["current"]
    list_filter = ("current",)
    ordering = ("name",)
    form = SongForm
    prepopulated_fields = {"slug": ["name"]}


admin.site.unregister(FlatPage)
admin.site.unregister(Invitation)


@admin.register(FlatPage)
class MarkdownxFlatPageAdmin(FlatPageAdmin):
    class Media:
        css = {"all": ("https://unpkg.com/tiny-markdown-editor/dist/tiny-mde.min.css",)}
        js = (
            "https://unpkg.com/tiny-markdown-editor/dist/tiny-mde.min.js",
        )


@admin.register(Invitation)
class ResendInvitationAdmin(InvitationAdmin):
    actions = ["resend_invitation"]

    @admin.action(description="Resend invitation")
    def resend_invitation(self, request, queryset):
        for invitation in queryset:
            invitation.send_invitation(request)
        num = queryset.count()
        self.message_user(
            request,
            f"{num} invitation{'' if num == 1 else 's'} have been resent."
        )
