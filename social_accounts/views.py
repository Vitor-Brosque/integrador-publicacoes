from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import SocialAccountIntegrationForm
from .models import SocialAccount
from .services import (
    get_integration_config,
    get_platform_dashboard_cards,
    get_social_account_for_platform,
    get_social_account_initial_data,
)


def integrations_dashboard(request):
    return render(
        request,
        "social_accounts/integrations_dashboard.html",
        {
            "cards": get_platform_dashboard_cards(),
        },
    )


def platform_integration(request, platform_slug):
    try:
        config = get_integration_config(platform_slug)
    except KeyError as exc:
        raise Http404("Plataforma não encontrada.") from exc

    account = get_social_account_for_platform(config["platform"])

    if request.method == "POST":
        form = SocialAccountIntegrationForm(request.POST)
        if form.is_valid():
            account = form.save(
                instance=account or SocialAccount(platform=config["platform"]),
                platform=config["platform"],
            )
            messages.success(
                request,
                f"Configuração de {config['label']} salva com sucesso.",
            )
            return redirect(
                "social_accounts:platform_integration",
                platform_slug=config["slug"],
            )
    else:
        form = SocialAccountIntegrationForm(
            initial=get_social_account_initial_data(account),
        )

    return render(
        request,
        "social_accounts/platform_integration.html",
        {
            "account": account,
            "config": config,
            "form": form,
            "token_state": "configurado" if account and account.access_token else "vazio",
        },
    )
