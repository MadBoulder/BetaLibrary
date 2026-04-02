# Claude Instructions for BetaLibrary

## Git: no hacer commit ni push sin permiso explícito

Nunca hacer commit ni push de cambios sin que el usuario lo pida explícitamente.

## Templates generadas automáticamente

La carpeta `templates/` contiene archivos generados automáticamente por scripts (`generate_pages.py`, `generate_boulder_pages.py`, etc.). **No hay que commitear ni subir estos archivos** porque ya existe un script programado que actualiza la web una vez al día y regenera las templates.

Si se detectan cambios en templates generadas durante el trabajo, ignorarlos y no incluirlos en commits.
