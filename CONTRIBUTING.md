# Guía de Contribución a AutogestiónPro

¡Gracias por tu interés en contribuir a AutogestiónPro! Valoramos tus aportaciones y queremos que el proceso sea lo más fluido posible.

## Cómo Contribuir

1.  **Fork el Repositorio:** Comienza haciendo un "fork" de este repositorio a tu propia cuenta de GitHub.
2.  **Clona tu Fork:** Clona tu repositorio bifurcado a tu máquina local:
    ```bash
    git clone https://github.com/tu-usuario/autogestionpro.git
    ```
3.  **Crea una Rama (Branch):** Crea una nueva rama para tus cambios. Usa un nombre descriptivo para tu rama (ej. `feature/nombre-de-la-funcionalidad`, `bugfix/descripcion-del-bug`).
    ```bash
    git checkout -b feature/tu-nueva-funcionalidad
    ```
4.  **Realiza tus Cambios:** Implementa tus mejoras o correcciones. Asegúrate de seguir las convenciones de código existentes en el proyecto.
5.  **Pruebas:** Si tus cambios incluyen nuevas funcionalidades o corrigen bugs, por favor, añade o actualiza las pruebas unitarias y de integración correspondientes. Asegúrate de que todas las pruebas existentes pasen.
6.  **Documentación:** Actualiza cualquier documentación relevante (READMEs, guías de configuración, etc.) que se vea afectada por tus cambios.
7.  **Commits:** Realiza commits atómicos y descriptivos. Cada commit debe representar un cambio lógico y completo.
    ```bash
    git commit -m "feat: Añade nueva funcionalidad X"
    ```
8.  **Sincroniza tu Rama:** Antes de enviar tu Pull Request, asegúrate de que tu rama esté actualizada con la rama `main` del repositorio original.
    ```bash
    git pull origin main
    ```
9.  **Envía tu Rama:** Sube tu rama a tu repositorio bifurcado.
    ```bash
    git push origin feature/tu-nueva-funcionalidad
    ```
10. **Crea un Pull Request (PR):** Abre un Pull Request desde tu rama en tu fork hacia la rama `main` del repositorio original de AutogestiónPro.
    *   Proporciona una descripción clara y concisa de tus cambios.
    *   Haz referencia a cualquier issue relevante.
    *   Asegúrate de que las pruebas automatizadas pasen.

## Estándares de Código

*   **Formato:** Sigue el formato de código existente. Utiliza herramientas de formateo si el proyecto las tiene configuradas (ej. Black para Python, Prettier para JavaScript).
*   **Nomenclatura:** Utiliza nombres de variables, funciones y clases descriptivos y consistentes.
*   **Comentarios:** Añade comentarios cuando sea necesario para explicar lógica compleja o decisiones de diseño.
*   **Tipado:** Si el lenguaje lo soporta (ej. Python con type hints, TypeScript), utiliza el tipado para mejorar la claridad y la robustez del código.

## Consideraciones de Seguridad

*   Nunca incluyas credenciales, claves API o información sensible directamente en el código.
*   Asegúrate de que tus cambios no introduzcan vulnerabilidades de seguridad.

¡Esperamos tus contribuciones!
