# WeChat Official Account (MP) API Reference

Base URL: `https://api.weixin.qq.com/cgi-bin`

All calls require a valid `access_token` (except `/token` itself). The caller's egress IP
must be in the MP platform IP whitelist, or the API returns `40164` / `40013` style errors.

## Get access_token
```
GET /token?grant_type=client_credential&appid=APPID&secret=APPSECRET
```
Response: `{ "access_token": "...", "expires_in": 7200 }`
Cache it (~7200s) to avoid rate limits. The publisher stores it in `token.json`.

## Upload cover image (permanent material)
```
POST /material/add_material?access_token=TOKEN&type=image
multipart field "media" = image file
```
Response: `{ "media_id": "...", "url": "..." }`
Use `media_id` as `thumb_media_id` in `draft/add`. Cover must meet MP size/ratio rules
(recommended ≥ 900×383, JPG/PNG, ≤ 10MB).

## Upload inline content image
```
POST /media/uploadimg?access_token=TOKEN
multipart field "media" = image file
```
Response: `{ "url": "https://mmbiz.qpic.cn/..." }`
Embed this `url` directly in the article HTML `<img src="...">`.

## Add draft
```
POST /draft/add?access_token=TOKEN
body: { "articles": [ { ... } ] }
```
Article fields:
- `title` (required)
- `author`
- `digest` (summary shown on the card)
- `content` (HTML, inline styles only)
- `thumb_media_id` (required — cover media_id)
- `need_open_comment` (0/1)
- `only_fans_can_comment` (0/1)
Response: `{ "media_id": "..." }`

## Submit / publish (mass send)
```
POST /freepublish/submit?access_token=TOKEN
body: { "media_id": "<from draft/add>" }
```
Response: `{ "publish_id": "..." }` — publishing is async.
Poll status with `POST /freepublish/get?access_token=TOKEN` body `{ "publish_id": "..." }`.

## Common error codes
| code | meaning |
|------|---------|
| 40001 | invalid credential / wrong appsecret |
| 40013 | invalid appid |
| 41001 | missing access_token |
| 40007 | invalid media_id (cover problem) |
| 45009 | mass-send count limit reached |
| 48001 | API unauthorized for this account type (e.g. subscribe account lacks perms) |
| 40164 | IP not in whitelist |
| 45064 | draft content empty / invalid |

Tip: a `40007` on `draft/add` almost always means the cover image failed to upload or its
`media_id` is stale — re-upload the cover and retry.
