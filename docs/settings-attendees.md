# Attendees Settings

The Attendees tab controls how meeting participants are classified and displayed in the countdown window.

## Organization

### Internal Email Domain

Your company's email domain (e.g., `acme.com`). This tells the app how to classify meeting attendees:

- **Internal attendees** — email addresses matching this domain.
- **External attendees** — everyone else, grouped by their email domain with organization favicons.

The countdown window's attendee summary line (e.g., "8 attendees · 5 internal, 3 external from 2 orgs") depends on this being set. If left blank, all attendees appear in a single flat list without internal/external classification.

> This field used to live on the General tab; if you're following an older guide, look here instead.

**Default:** Empty

## Employee Directory

### Directory URL Template

When set, **internal** attendee names in the countdown window become clickable links that open this URL in your default browser. Leave blank to disable — there is no separate enable toggle.

Only internal attendees become clickable. External attendees are never linked, since the right directory for them depends on which company they work at.

#### Variables

Given an attendee `jane.doe@acme.com`:

| Token | Value |
|---|---|
| `{Email}` | `jane.doe@acme.com` |
| `{Username}` | `jane.doe` |
| `{Domain}` | `acme.com` |

All substitutions are URL-encoded before insertion, so emails containing `+` or other reserved characters work correctly. Tokens that don't appear in your template are simply ignored.

#### Worked examples

**1. Custom internal directory (the canonical case)**

Most companies run a homegrown or vendor directory (Workday, BambooHR, Rippling, custom SharePoint, internal "people" site) at a known URL pattern. Pick the variable that matches your URL shape:

```
https://directory.acme.com/u/{Username}
https://people.acme.com/profile?email={Email}
https://intranet.acme.com/employees/{Username}
```

`{Username}` is usually right when the URL uses a slug; `{Email}` when it uses a query parameter.

**2. Microsoft 365 profile (Delve / SharePoint)**

Microsoft 365 exposes each employee's profile page — with org chart, contact info, recent docs, and reporting line — at a tenant-scoped URL that accepts an email address as a query parameter. This is the closest thing to a built-in M365 employee directory deep link, and is the recommended setting for any team on Microsoft 365 / Office 365:

```
https://acmecorp-my.sharepoint.com/_layouts/15/me.aspx/?p={Email}&v=work
```

Replace `acmecorp` with your organization's SharePoint tenant slug (the part before `-my.sharepoint.com` when you visit your own OneDrive). Microsoft now redirects these to the unified microsoft365.com profile experience, so the same URL keeps working as the surface evolves. Since the tenant slug is a constant in your template, it isn't a substitution variable — only `{Email}`, `{Username}`, and `{Domain}` are substituted at click time.

**3. Glean**

Glean's people search is keyed off email and lands on the matching person's profile. The exact path depends on your Glean tenant, but the general shape is:

```
https://app.glean.com/search?q={Email}&t=people
```

Glean does not publicly document a stable profile-by-email deep link, so confirm the URL pattern against your own Glean instance before relying on it.

#### Known limitations

- **Microsoft Teams org chart** — Teams' Org Explorer does not expose a public deep link by email. The only documented Teams deep links accepting an email are for starting *chats*, not for opening a profile/org-chart view.
- **Slack profiles / DMs** — Slack's deep-link scheme requires Slack's internal user ID and team ID, not an email. Since this app only knows the attendee's email, Slack is not a viable directory target.
- **Google Workspace** — Google does not publish a stable per-employee profile deep link keyed on email. Users on Google Workspace will typically fall back to category 1 (a custom internal directory).

**Default:** Empty (feature disabled)
