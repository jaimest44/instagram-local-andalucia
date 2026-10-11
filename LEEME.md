# Instagram automático · @localandalucia

Publica cada día a las 20:30 (hora de Madrid) un carrusel generado a partir de los Excel corregidos.
Funciona igual que el de @administrativo_local_andalucia, con su propio repositorio y su propia cola.

```
PC (cada lunes)                                          GitHub Actions (cada día)
Excel + codificado → filtro de calidad → carruseles → cola/  →  publicador → API de Instagram
```

## Rotación

Un día cada cosa, en este orden y sin parar: **test → supuesto → infracción → test → …**

Formatos:
- **Test**: pregunta · solución + artículo literal · la trampa · llamada a la app.
- **Supuesto**: el caso · pregunta a desarrollar · solución · llamada a la app.
- **Infracción del codificado**: la conducta y "¿leve, grave o muy grave?" · solución con precepto, cuantía, puntos, responsable y órgano competente · llamada a la app.

## De dónde sale el contenido

| Tipo | Carpeta |
|---|---|
| Test | `10. TEST/20. SOLUCIÓN EXCEL/BBDD CORREGIDA` |
| Supuestos | `11. SUPUESTOS PRÁCTICOS/20. SOLUCIÓN EXCEL SP/SUBIDOS` |
| Infracciones | `20. RECURSOS IA/CODIFICADO` (la subcarpeta `otros` no se usa) |

El filtro de calidad (`python generador/datos.py` muestra el informe) descarta, entre otras:
- preguntas que no caben legibles en un carrusel;
- preguntas que dependen de una imagen o que están incompletas;
- encabezados de supuesto que no son preguntas ("Normativa aplicable.");
- normas derogadas: Ley 13/2001 de coordinación de policías locales, LO 1/1992, RDL 339/1990, Ley 30/1992...;
- infracciones cuyo texto ya dice si es leve, grave o muy grave.

## Tareas habituales

- **Quitar o cambiar una publicación** antes de que salga: borra o edita la carpeta de ese día en `cola/` y sube el cambio.
- **Que algo no salga nunca**: corrígelo en el Excel, o añade su id (está en `meta.json`) a `estado/usadas.json`.
- **Probar sin publicar**: GitHub > Actions > Publicar en Instagram > Run workflow, con el modo `simular` o `comprobar`.

## Configuración inicial (una sola vez)

La app de Meta es la misma que la de Administrativo (`Local_Andalucia`, App ID `1120351110370238`), que ya tiene los permisos.

1. La cuenta @localandalucia tiene que ser **profesional** y estar vinculada a **su página de Facebook**.
2. En el Explorador de la API Graph, genera un token nuevo con los mismos permisos y, en la ventana de Facebook, marca también la página e Instagram de Local Andalucía.
3. Desde ESTA carpeta (`LOCAL ANDALUCÍA/40. INSTAGRAM`), ejecuta `python publicador/configurar_token.py` y elige la cuenta @localandalucia en la lista.
4. GitHub > Actions > Publicar en Instagram > Run workflow > modo `comprobar`.
