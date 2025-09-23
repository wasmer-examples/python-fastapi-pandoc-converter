import asyncio
import html
from typing import List

import pypandoc
from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi import Body

app = FastAPI(title="pandoc-converter")

SUPPORTED_FORMATS: List[tuple[str, str]] = [
    ("markdown", "Markdown"),
    ("rst", "reStructuredText"),
    ("html", "HTML"),
    ("latex", "LaTeX"),
    ("mediawiki", "MediaWiki"),
    ("docbook", "DocBook"),
    ("org", "Org Mode"),
]

ROOT_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Pandoc Converter</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css" />
    <script
      src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.7/dist/htmx.min.js"
      integrity="sha384-ZBXiYtYQ6hJ2Y0ZNoYuI+Nq5MqWBr+chMrS/RkXpNzQCApHEhOt2aY8EJgqwHLkJ"
      crossorigin="anonymous">
    </script>
  </head>
  <body class="has-background-light">
    <section class="section">
      <div class="container">
        <h1 class="title">Pandoc Converter</h1>
        <p class="subtitle">Convert text between markup formats without leaving your browser.</p>
        <p>
          Hint: You can also use the <a href="/docs">REST API</a>.
        </p>
        <br />
        <form
          class="box"
          hx-post="/api/hx/convert"
          hx-target="#conversion-result"
          hx-swap="innerHTML"
          hx-disabled-elt=".button-submit"
          hx-on::beforeRequest="document.getElementById('convert-button').classList.add('is-loading')"
          hx-on::afterRequest="document.getElementById('convert-button').classList.remove('is-loading')">
          <div class="columns">
            <div class="column">
              <div class="field">
                <label class="label" for="source_format">Source Format</label>
                <div class="control">
                  <div class="select is-fullwidth">
                    <select id="source_format" name="source_format" required>
                      {format_options}
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div class="column">
              <div class="field">
                <label class="label" for="target_format">Target Format</label>
                <div class="control">
                  <div class="select is-fullwidth">
                    <select id="target_format" name="target_format" required>
                      {format_options}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="field">
            <label class="label" for="text">Source Text</label>
            <div class="control">
              <textarea class="textarea" id="text" name="text" rows="12" placeholder="Enter your content here..." required></textarea>
            </div>
          </div>
          <div class="field is-grouped is-grouped-right">
            <p class="control">
              <button id="convert-button" type="submit" class="button is-primary button-submit">Convert</button>
            </p>
          </div>
        </form>
        <div id="conversion-result"></div>
      </div>
    </section>
  </body>
</html>
"""

ERROR_TEMPLATE = r"""
<article class="message is-danger">
  <div class="message-header">
    <p>Conversion Failed</p>
  </div>
  <div class="message-body">{escaped_error}</div>
</article>
"""


SUCCESS_TEMPLATE = r"""
<article class="message is-success">
  <div class="message-header">
    <p>Conversion Result</p>
  </div>
  <div class="message-body">
    <textarea class="textarea" rows="12" readonly>{escaped_result}</textarea>
  </div>
</article>
"""


def _format_options() -> str:
    options = []
    for value, label in SUPPORTED_FORMATS:
        options.append(f'<option value="{value}">{html.escape(label)}</option>')
    return "\n".join(options)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root() -> str:
    format_options = _format_options()
    return ROOT_TEMPLATE.replace("{format_options}", format_options)


@app.post("/api/hx/convert", response_class=HTMLResponse, include_in_schema=False)
async def convert(
    text: str = Form(...),
    source_format: str = Form(...),
    target_format: str = Form(...),
) -> str:
    # import time; time.sleep(5)
    try:
        converted = await asyncio.to_thread(
            pypandoc.convert_text,
            text,
            to=target_format,
            format=source_format,
        )
    except (RuntimeError, OSError) as exc:
        escaped_error = html.escape(str(exc))
        return ERROR_TEMPLATE.replace("{escaped_error}", escaped_error)

    escaped_result = html.escape(converted)
    return SUCCESS_TEMPLATE.replace("{escaped_result}", escaped_result)


@app.get(
    "/api/pandoc-convert",
    summary="Convert text using Pandoc (GET)",
    description=(
        "Converts the provided text from one markup format to another using Pandoc. "
        "All parameters are provided via query string."
    ),
)
async def api_pandoc_convert_get(
    from_: str = Query(
        ..., alias="from", description="Source format (e.g., 'markdown', 'rst', 'html')."
    ),
    to: str = Query(..., description="Target format to convert to."),
    text: str = Query(..., description="Input text to convert."),
):
    """
    Example
    -------
    curl --get 'http://localhost:8000/api/pandoc-convert' \\
      --data-urlencode 'from=markdown' \\
      --data-urlencode 'to=html' \\
      --data-urlencode 'text=# Hello\n\nThis is **Markdown**.'
    """
    try:
        converted = await asyncio.to_thread(
            pypandoc.convert_text,
            text,
            to=to,
            format=from_,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    return PlainTextResponse(converted)


@app.post(
    "/api/pandoc-convert",
    summary="Convert text using Pandoc (POST)",
    description=(
        "Converts text using Pandoc. Query parameters define formats; the request body "
        "must include form field 'text' (multipart/form-data or application/x-www-form-urlencoded)."
    ),
)
async def api_pandoc_convert_post(
    from_: str = Query(
        ..., alias="from", description="Source format (e.g., 'markdown', 'rst', 'html')."
    ),
    to: str = Query(..., description="Target format to convert to."),
    text: str = Form(..., description="Input text to convert."),
):
    """
    Example
    -------
    curl -X POST 'http://localhost:8000/api/pandoc-convert?from=markdown&to=html' \\
      -F 'text=# Hello\n\nThis is **Markdown**.'
    """
    # POST expects query params 'from' and 'to' and form field 'text'

    try:
        converted = await asyncio.to_thread(
            pypandoc.convert_text,
            text,
            to=to,
            format=from_,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    return PlainTextResponse(converted)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
