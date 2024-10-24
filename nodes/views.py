import os
import json
from copy import deepcopy
from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import render
import markdown
import nh3
from .models import Node


BASE_DIR = "information_system/"
DEFAULT_RENDERING_METHOD = "txt_render"
AUTOMATIC_RENDER_LOOKUP = {
    "main.html": "html_safe_render",
    "main.md": "markdown_render",
    "main.txt": "txt_render",
}


# TODO: Fix path traversal vulnerability
# TODO:
def serve_node_file(request, node_path, file_name):
    file_path_full = os.path.join(BASE_DIR, node_path, file_name)

    if not os.path.exists(file_path_full):
        raise Http404("File not found")

    return FileResponse(
        open(file_path_full, "rb"), content_type="application/octet-stream"
    )


def render_node_with_query_handling(request, node_path=""):
    file_name = request.GET.get("file")
    if file_name:
        return serve_node_file(request, node_path, file_name)
    else:
        return render_node(request, node_path)


def load_file_or_404(node_dir, file_name, error_message):
    file_path = os.path.join(node_dir, file_name)
    if not os.path.exists(file_path):
        raise Http404(error_message)
    with open(file_path, "r") as file:
        return file.read()


def html_safe_render(node_dir, node_path, request):
    # TODO: disable classless css here if using for page archive

    safe_html_content = nh3.clean(
        load_file_or_404(node_dir, "main.html", "Main HTML file not found")
    )

    context = {
        "content": safe_html_content,
        "node_path": node_path,
        "base_dir": BASE_DIR,
    }
    return render(request, "node_templates/html_safe_node.html", context)


def markdown_render(node_dir, node_path, request):
    markdown_content = load_file_or_404(
        node_dir, "main.md", "Main markdown file not found"
    )
    md = markdown.Markdown(extensions=["mdx_wikilink_plus"])
    html_content = md.convert(markdown_content)

    context = {
        "content": html_content,
        "node_path": node_path,
        "base_dir": BASE_DIR,
    }
    return render(request, "node_templates/markdown_node.html", context)


def txt_render(node_dir, node_path, request):
    txt_content = load_file_or_404(node_dir, "main.txt", "Main txt file not found")
    context = {
        "content": txt_content,
        "node_path": node_path,
        "base_dir": BASE_DIR,
    }
    return render(request, "node_templates/txt_node.html", context)


RENDERING_METHODS = {
    "markdown_render": markdown_render,
    "txt_render": txt_render,
    "html_safe_render": html_safe_render,
}


def render_node(request, node_path):
    node_dir = os.path.join(BASE_DIR, node_path)
    metadata_file = os.path.join(node_dir, "metadata.json")
    rendering_method_name = None

    if not os.path.isdir(node_dir):
        raise Http404("Node not found")

    if os.path.isfile(metadata_file):
        with open(metadata_file, "r") as file:
            metadata = json.load(file)
            rendering_method_name = metadata.get("rendering_method")

    main_file = None

    if rendering_method_name is None:
        main_file = next(
            (
                file
                for file in AUTOMATIC_RENDER_LOOKUP
                if os.path.isfile(os.path.join(node_dir, file))
            ),
            None,
        )

        if main_file is None:
            raise Http404("No main file found")
        rendering_method_name = AUTOMATIC_RENDER_LOOKUP[main_file]

    rendering_method = RENDERING_METHODS[rendering_method_name]

    return rendering_method(node_dir, node_path, request)
