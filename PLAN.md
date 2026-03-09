# Plan: Rediseño Admin Panel — Estilo WhatsApp Web + Marca STICK

## Objetivo
Transformar el panel admin actual en una interfaz estilo WhatsApp Web, usando la paleta de colores y tipografía de STICK. El panel debe verse profesional, moderno y familiar para cualquier usuario que haya usado WhatsApp Web.

---

## Paleta de Colores STICK (del manual de marca)

| Nombre         | HEX       | Uso en el panel                                    |
|----------------|-----------|-----------------------------------------------------|
| Azul oscuro    | `#364c85` | Header sidebar, header chat, botones primarios       |
| Azul medio     | `#95b2ee` | Burbuja mensajes bot (izquierda), acentos hover      |
| Celeste claro  | `#d0d9f6` | Fondo chat area, bordes suaves, badges               |
| Verde claro    | `#e7f1ac` | Burbuja mensajes paciente (derecha), indicadores OK   |
| Blanco         | `#ffffff` | Fondo sidebar, fondo cards, textos sobre azul        |

**Tipografía:** Nunito (Google Fonts) — Regular 400, SemiBold 600, Bold 700

---

## Layout General (estilo WhatsApp Web)

```
┌─────────────────────────────────────────────────────────┐
│ Toda la pantalla, sin header superior                   │
├──────────────┬──────────────────────────────────────────┤
│  SIDEBAR     │  CHAT AREA                               │
│  (380px)     │  (flex-1)                                │
│              │                                          │
│ ┌──────────┐ │ ┌──────────────────────────────────────┐ │
│ │ Header   │ │ │ Chat Header (paciente info + acciones)│ │
│ │ STICK    │ │ ├──────────────────────────────────────┤ │
│ │ logo +   │ │ │                                      │ │
│ │ admin    │ │ │  Mensajes con burbujas               │ │
│ ├──────────┤ │ │  (fondo con pattern sutil)           │ │
│ │ Buscador │ │ │                                      │ │
│ ├──────────┤ │ │  Bot ← izq (azul medio)             │ │
│ │          │ │ │  Paciente → der (verde claro)        │ │
│ │ Lista de │ │ │                                      │ │
│ │ convos   │ │ │  Tool calls colapsados               │ │
│ │          │ │ │                                      │ │
│ │ (scroll) │ │ ├──────────────────────────────────────┤ │
│ │          │ │ │ Input bar (simular mensaje)          │ │
│ └──────────┘ │ └──────────────────────────────────────┘ │
└──────────────┴──────────────────────────────────────────┘
```

---

## Pasos de Implementación

### Paso 1: Theme & Fuente (globals.css + layout.tsx)
**Archivos:** `globals.css`, `layout.tsx`

- Reemplazar Geist font por **Nunito** (Google Fonts)
- Reemplazar colores OKLCH neutros por paleta STICK:
  - `--color-primary` → `#364c85`
  - `--color-primary-foreground` → `#ffffff`
  - `--color-secondary` → `#95b2ee`
  - `--color-accent` → `#e7f1ac`
  - `--color-muted` → `#d0d9f6`
  - `--color-background` → `#d0d9f6` (celeste claro, como WhatsApp)
  - `--color-card` → `#ffffff`
- Agregar CSS para el pattern de fondo del chat (SVG sutil tipo WhatsApp)
- Variables adicionales para burbujas:
  - `--bubble-bot` → `#ffffff` (blanco, como WhatsApp)
  - `--bubble-patient` → `#e7f1ac` (verde claro STICK)

### Paso 2: Login Page (login/page.tsx + LoginForm.tsx)
**Archivos:** `login/page.tsx`, `LoginForm.tsx`

- Fondo: gradiente azul oscuro → azul medio
- Card centrada con logo STICK arriba
- Campos con estilo limpio, bordes celeste claro
- Botón login: azul oscuro con hover azul medio
- Subtítulo: "Panel de Administración — Bot Sofia"

### Paso 3: Sidebar - Conversation List (dashboard layout + ConversationList.tsx)
**Archivos:** `dashboard/layout.tsx`, `dashboard/page.tsx`, `conversations/[id]/page.tsx`, `ConversationList.tsx`

- **Eliminar header superior** (mover info admin al header de sidebar)
- Header sidebar:
  - Fondo azul oscuro (`#364c85`)
  - Logo STICK (isotipo blanco) a la izquierda
  - Nombre admin + botón logout (iconos blancos) a la derecha
- Barra de búsqueda debajo del header (estilo WhatsApp: fondo gris claro, icono lupa)
- Items de conversación:
  - Avatar circular con iniciales del paciente (fondo azul medio)
  - Nombre paciente (bold) + timestamp (gris, derecha)
  - Preview último mensaje (gris, truncado 1 línea)
  - Badge de estado: punto verde (activa), amarillo (esperando), naranja (takeover)
  - Badge de mensajes no leídos (circulito verde claro con número)
  - Hover: fondo celeste muy claro
  - Activa: fondo celeste claro con borde izq azul oscuro
- Ancho sidebar: 380px (más amplio que el actual 320px)
- Separador sutil entre items

### Paso 4: Chat Area - Header (ChatView.tsx)
**Archivos:** `ChatView.tsx`

- Header chat: fondo `#f0f2f5` (gris WhatsApp-like) o blanco
  - Avatar paciente (izquierda) con iniciales
  - Nombre paciente + teléfono debajo (fuente más chica, gris)
  - Status badge (Activa / Bot / Admin Takeover)
  - Botones de acción (derecha):
    - Toggle takeover (icono persona/robot)
    - Botón info (futuro)

### Paso 5: Chat Area - Mensajes (ChatView.tsx)
**Archivos:** `ChatView.tsx`

- Fondo chat: celeste muy claro (`#d0d9f6` al 30% opacidad) + pattern SVG sutil
- Burbujas de mensaje:
  - **Paciente (derecha):** fondo verde claro `#e7f1ac`, cola apuntando derecha
  - **Bot/Admin (izquierda):** fondo blanco `#ffffff`, sombra sutil, cola apuntando izquierda
  - Timestamp dentro de la burbuja (abajo-derecha, gris chico)
  - Bordes redondeados estilo WhatsApp (más redondeados que los actuales)
  - Max-width: 65% del contenedor
- Tool calls: cards colapsadas entre mensajes
  - Estilo "system message" centrado
  - Icono de herramienta + nombre + duración
  - Click para expandir/colapsar (input/output en JSON)
  - Color: fondo celeste claro, borde azul medio
- Scroll suave, auto-scroll al último mensaje

### Paso 6: Chat Area - Input Bar (ChatView.tsx)
**Archivos:** `ChatView.tsx`

- Barra inferior fija:
  - Fondo blanco/gris claro
  - Campo teléfono (solo si es simulación): compacto, a la izquierda
  - Campo mensaje: flexible, bordes redondeados, fondo blanco
  - Botón enviar: circular, azul oscuro, icono flecha
- Estilo WhatsApp: input ocupa casi todo el ancho

### Paso 7: Estado vacío + Detalles finales
**Archivos:** `dashboard/page.tsx`, varios

- Pantalla vacía (sin conversación seleccionada):
  - Logo STICK grande centrado (opacidad baja)
  - Texto: "Seleccioná una conversación para ver los mensajes"
  - Fondo: celeste claro
- Loading states: skeleton con colores STICK
- Animaciones suaves: transiciones de 200ms en hover, apertura de tool calls
- Responsive: en mobile, sidebar ocupa todo; al seleccionar convo, muestra chat full-screen

### Paso 8: Logo STICK como asset
**Archivos:** `public/stick-logo.svg`, `public/stick-isotipo.svg`

- Crear SVG del isotipo STICK para usar en sidebar header
- Crear SVG del logo horizontal para login y estado vacío
- Si no tenemos SVG, usar texto estilizado "STICK" con la tipografía correcta

---

## Archivos que se modifican

| Archivo | Cambio |
|---------|--------|
| `globals.css` | Paleta STICK, Nunito font, pattern CSS, bubble styles |
| `layout.tsx` | Reemplazar Geist por Nunito (Google Fonts) |
| `login/page.tsx` | Fondo gradiente, estilo STICK |
| `LoginForm.tsx` | Colores y estilo STICK |
| `dashboard/layout.tsx` | Eliminar header superior, layout full-screen |
| `dashboard/page.tsx` | Estado vacío con logo, sidebar + main area |
| `conversations/[id]/page.tsx` | Sidebar + chat area layout |
| `ConversationList.tsx` | Rediseño completo estilo WhatsApp |
| `ChatView.tsx` | Burbujas, header, input bar, fondo pattern |
| `ToolCallCard.tsx` | Estilo system message, colores STICK |

**Archivos nuevos:**
| Archivo | Qué es |
|---------|--------|
| `public/stick-logo.svg` | Logo horizontal STICK |
| `public/stick-isotipo.svg` | Isotipo STICK |

---

## NO se modifica
- `api.ts` — sin cambios de API
- `types.ts` — sin cambios de tipos
- `ws.ts` — sin cambios de WebSocket
- `utils.ts` — sin cambios
- shadcn/ui components (`button.tsx`, `card.tsx`, etc.) — se mantienen, se overridean con clases

---

## Orden de ejecución
1. Theme + Font (base para todo)
2. Login (entrada al sistema)
3. Layout + Sidebar (estructura principal)
4. Chat header + mensajes + input (funcionalidad core)
5. Detalles finales (estado vacío, animaciones, responsive)

Total estimado: ~8 pasos, todo en el frontend existente sin romper funcionalidad.
