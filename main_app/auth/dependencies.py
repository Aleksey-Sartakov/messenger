from main_app.auth.services.auth_service import auth_service


current_active_user_or_none = auth_service.current_user(active=True, optional=True)

current_active_user = auth_service.current_user(active=True)

current_admin_user = auth_service.current_user(active=True, superuser=True)