from django.shortcuts import render, redirect
from django.db import connection

def get_all_apis():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name, url, description FROM api_registry ORDER BY id;")
        rows = cursor.fetchall()
    return [{"id": r[0], "name": r[1], "url": r[2], "description": r[3]} for r in rows]

def add_api(name, url, description):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO api_registry (name, url, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
        """, [name, url, description])

def delete_api(api_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM api_registry WHERE id = %s;", [api_id])

def update_api(api_id, name, url, description):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE api_registry
            SET name=%s, url=%s, description=%s
            WHERE id=%s;
        """, [name, url, description, api_id])

def admin_view(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            add_api(
                request.POST.get("name"),
                request.POST.get("url"),
                request.POST.get("description")
            )
            return redirect("admin_view")

        if action == "delete":
            delete_api(request.POST.get("id"))
            return redirect("admin_view")

        if action == "update":
            update_api(
                request.POST.get("id"),
                request.POST.get("name"),
                request.POST.get("url"),
                request.POST.get("description")
            )
            return redirect("admin_view")

    apis = get_all_apis()
    return render(request, "admin.html", {"apis": apis})
