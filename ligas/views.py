from django.http import HttpResponse
def home(request):
    return HttpResponse("<h1>Sistema de Ligas</h1><p>Entrá al <a href='/admin/'>Admin</a>.</p>")
