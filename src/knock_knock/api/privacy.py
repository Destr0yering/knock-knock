from __future__ import annotations

import html
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["privacy"])


@router.get("/privacy", include_in_schema=False, response_class=HTMLResponse)
async def public_privacy_notice(request: Request) -> HTMLResponse:
    settings = request.app.state.container.settings
    name = settings.public_developer_name.strip()
    contact = settings.privacy_contact_email.strip()
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact):
        raise HTTPException(status_code=503, detail="Privacy notice is awaiting operator contact details")
    safe_name, safe_contact = html.escape(name), html.escape(contact)
    body = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Knock Knock Privacy Notice</title>
<main><h1>Knock Knock Privacy Notice</h1><p>Last updated: October 21, 2026</p>
<h2>Operator</h2><p>{safe_name}</p><p><a href="mailto:{safe_contact}">{safe_contact}</a></p>
<h2>Information and purpose</h2><p>Knock Knock uses Amazon Cognito for account sign-in. When you connect Ring through Ring's hosted Appstore flow, Knock Knock receives Ring account and device identifiers, event metadata and one still JPEG snapshot for supported events. It does not request or store Ring video clips. Ring may display permissions broader than the still-image workflow; review them before authorizing.</p>
<p>AWS services in US East (N. Virginia) support account linking, face detection and advisory Rekognition matching, encrypted image and visit storage. Each Ring owner's face collection is isolated. A face match is a suggestion and does not prove identity. Firebase Cloud Messaging receives a device token and generic alert data only after separate opt-in; notifications contain no visitor names or images. The Android app stores private journal records in an encrypted local database and vault.</p>
<p>Knock Knock also processes account identifiers, Ring OAuth tokens, consent records, push preferences, deletion-job status and limited operational metadata. Application logs are configured not to contain visitor images, names, tokens or face vectors.</p>
<h2>Retention</h2><p>Unsaved snapshots and face crops expire after 30 days; visit records after 365 days. Saved visitor media and active face references remain until removed or account deletion. Deletion receipts expire after 30 days, Ring webhook deduplication records after seven days, service logs after 14 days, and failed deletion messages after up to 14 days.</p>
<p>DynamoDB point-in-time recovery can retain deleted household and visit data in recoverable backups for up to 35 days. Backup copies expire on that schedule and are not used for normal app operation. A minimal deletion tombstone has an expiration set five minutes after the sign-in token expires to prevent that token from restarting processing; DynamoDB may physically remove it later.</p>
<h2>Your controls</h2><p>Disable push alerts in Knock Knock. To delete your account, sign in and type DELETE in the app. The service stops new Ring processing, removes active cloud records, images, Ring and push tokens, owner-specific face references and the Cognito account, then erases local app data. A one-time receipt checks progress after sign-out. Completion is reported only after primary data cleanup succeeds; backup and operational retention periods still apply.</p>
<p>To revoke Ring's side of its one-way Appstore link, open Ring Appstore &gt; My Apps &gt; Knock Knock &gt; Remove App. Ring invalidates its tokens and stops sending webhooks after removal. Knock Knock account deletion does not remove this Ring authorization for you.</p>
<h2>Sharing and safety</h2><p>Information is shared with Ring, Amazon Web Services, Amazon Cognito, Amazon Rekognition and Firebase Cloud Messaging as needed to provide these functions. Their privacy terms govern data they process. Knock Knock does not intentionally sell visitor information. Use only a camera you control, notify household members and visitors, obtain consent, and do not capture minors, neighbors or passersby. Do not use face analysis for emergency response, access control or consequential decisions.</p></main></html>"""
    return HTMLResponse(body, headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
    })
