"""Content models and the slug guarantees that protect search rankings."""

import pytest
from django.db import IntegrityError

from content.models import Banner, GalleryImage, Page, SiteSettings, Testimonial


@pytest.mark.django_db
class TestPage:
    def test_slug_is_unique(self):
        Page.objects.create(slug="fleet", title="Fleet")
        with pytest.raises(IntegrityError):
            Page.objects.create(slug="fleet", title="Fleet again")

    def test_homepage_url_is_root(self):
        page = Page.objects.create(
            slug="wwwaustinlimoshuttlecom", title="Home", page_type=Page.PageType.HOME,
        )
        assert page.url_path == "/"

    def test_other_pages_use_their_slug(self):
        page = Page.objects.create(slug="fleet", title="Fleet")
        assert page.url_path == "/fleet"

    def test_malformed_legacy_slugs_are_storable(self):
        """
        Two legacy slugs are URLs with the punctuation stripped. They must be
        preserved exactly -- they are live URLs with rankings attached.
        """
        for slug in ("wwwaustinlimoshuttlecom", "httpswwwaustinlimoshuttlecom"):
            page = Page.objects.create(slug=slug, title=slug)
            page.refresh_from_db()
            assert page.slug == slug

    def test_parent_can_be_orphaned_without_deleting_children(self):
        parent = Page.objects.create(slug="services", title="Services")
        child = Page.objects.create(slug="weddings", title="Weddings", parent=parent)
        parent.delete()
        child.refresh_from_db()
        assert child.parent is None


@pytest.mark.django_db
class TestBanner:
    def test_null_page_means_homepage(self):
        banner = Banner.objects.create(title="Spring offer")
        assert banner.page is None

    def test_deleting_a_page_keeps_its_banner(self):
        page = Page.objects.create(slug="fleet", title="Fleet")
        banner = Banner.objects.create(title="B", page=page)
        page.delete()
        banner.refresh_from_db()
        assert banner.page is None


@pytest.mark.django_db
class TestSiteSettingsSingleton:
    def test_always_one_row(self):
        SiteSettings.load()
        other = SiteSettings(contact_email="ops@example.com")
        other.save()
        assert SiteSettings.objects.count() == 1
        assert SiteSettings.load().contact_email == "ops@example.com"


@pytest.mark.django_db
class TestOrdering:
    def test_gallery_groups_by_category_then_order(self):
        GalleryImage.objects.create(title="b", category=GalleryImage.Category.PARTNER,
                                    display_order=1)
        GalleryImage.objects.create(title="a", category=GalleryImage.Category.GALLERY,
                                    display_order=2)
        assert [g.title for g in GalleryImage.objects.all()] == ["a", "b"]

    def test_testimonials_order_by_display_order(self):
        Testimonial.objects.create(customer_name="Second", quote="q", display_order=2)
        Testimonial.objects.create(customer_name="First", quote="q", display_order=1)
        assert [t.customer_name for t in Testimonial.objects.all()] == ["First", "Second"]
