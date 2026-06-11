from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings
from .forms import CustomUserCreationForm


def register_view(request):
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        messages.warning(
            request,
            'El registro público está deshabilitado. Solicitá el alta a un administrador.'
        )
        return redirect('login')

    if request.user.is_authenticated:
        return redirect('cv_list')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                'Cuenta creada correctamente. Ya podés comenzar a cargar perfiles profesionales.'
            )

            return redirect('cv_list')

        messages.error(
            request,
            'No se pudo crear la cuenta. Revisá los datos ingresados.'
        )

    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})
