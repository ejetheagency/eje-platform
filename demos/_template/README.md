# demos/_template

The layout and copy for every prospect demo. **Data is fully separated from presentation**, so a new prospect
never touches HTML.

## New prospect in four steps

```bash
mkdir -p demos/<prospecto>
cp demos/_template/config.json demos/<prospecto>/config.json   # edita: prospecto, titulo, pie, temporada, oferta, contacto
#   investiga y escribe demos/<prospecto>/leads.json           # siguiendo .claude/skills/account-demo/SKILL.md
python3 demos/_template/build.py <prospecto>                   # escribe demos/<prospecto>/index.html
```

`index.html` is generated and self-contained: it opens locally with no server. **Never hand-edit it**, the next
build overwrites it.

## What lives where

| Archivo | Qué contiene |
|---|---|
| `build.py` | Layout, estilos y toda la lógica de render. Lo único que se comparte entre prospectos. |
| `config.json` | Marca (4 colores), título, pie, countdown de temporada, línea de oferta, bloque de cierre (plan, correo, WhatsApp, referido). |
| `<prospecto>/leads.json` | Las cuentas: empresas, hooks, puertas, correos, evidencia, rutas, coach, resumen del día. |

## Las reglas que el generador aplica solo

Estas no dependen de que alguien se acuerde:

- un **buzón de área** nunca precarga el mailto primario (llega a quien conteste, no a quien decide);
- una **plantilla de patrón** (`<inicial><apellido>@dominio`) nunca llega a un campo `To:`;
- una **ruta débil** (buzón de ventas) se muestra pero no se precarga;
- un valor que falta en config se pinta como **`falta`** en rojo, nunca como placeholder ni inventado;
- el build **falla** si se cuela un em dash.

## Reglas de contenido

Viven en `.claude/skills/account-demo/SKILL.md` y son la definición de terminado: selección de cuentas, puertas,
lista de métodos para correos, reglas de conteo, vigencia, evidencia, objetivos duros y verificación.
