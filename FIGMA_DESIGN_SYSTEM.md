# REESTRY UI - Design System для Figma

## 🎨 Цветовая палитра

### Основные цвета
```
Primary: #2563eb (синий)
Primary Hover: #1d4ed8
Secondary: #64748b (серый)
Success: #10b981 (зеленый)
Error: #ef4444 (красный)
Warning: #f59e0b (оранжевый)
```

### Фоновые цвета
```
Background: #ffffff (белый)
Background Secondary: #f8fafc (светло-серый)
Border: #e2e8f0 (светло-серый)
```

### Текстовые цвета
```
Text Primary: #1e293b (темно-серый)
Text Secondary: #64748b (серый)
Text Muted: #94a3b8 (светло-серый)
```

## 📐 Spacing System

### Базовые отступы
```
4px   - минимальный отступ
8px   - маленький отступ
12px  - средний отступ
16px  - стандартный отступ
20px  - большой отступ
24px  - очень большой отступ
32px  - секционный отступ
```

### Радиусы скругления
```
4px  - маленький (--radius-sm)
8px  - стандартный (--radius)
12px - средний
20px - большой
```

## 🔤 Типографика

### Шрифты
```
Основной: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Roboto', 'Helvetica Neue', Arial, sans-serif
Моноширинный: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace (для кода)
```

### Размеры шрифтов
```
11px  - очень маленький (badges, labels)
12px  - маленький (метаданные, вторичный текст)
13px  - маленький-средний (описания)
14px  - базовый (основной текст)
16px  - средний (заголовки карточек)
20px  - большой (заголовки секций)
24px  - очень большой (главный заголовок)
```

### Веса шрифтов
```
300 - Light (закрытие модальных окон)
400 - Regular (обычный текст)
500 - Medium (labels, кнопки)
600 - SemiBold (заголовки, важный текст)
700 - Bold (акцентный текст)
```

## 🧩 Компоненты

### Кнопки

#### Primary Button
```
Background: #2563eb
Text: white
Padding: 10px 20px
Border Radius: 4px
Font Size: 14px
Font Weight: 500
Hover: Background #1d4ed8, transform translateY(-1px), shadow
```

#### Secondary Button
```
Background: #f8fafc
Text: #1e293b
Border: 1px solid #e2e8f0
Padding: 10px 20px
Border Radius: 4px
Hover: Background #e2e8f0
```

#### Danger Button
```
Background: #ef4444
Text: white
Padding: 10px 20px
Hover: Background #dc2626
```

#### Small Button
```
Padding: 6px 12px
Font Size: 12px
```

### Карточки

#### Prompt Card
```
Background: white
Border: 1px solid #e2e8f0
Border Radius: 8px
Padding: 20px
Shadow: 0 1px 3px rgba(0,0,0,0.1)
Hover: Border #2563eb, Shadow 0 4px 6px rgba(0,0,0,0.1)
```

#### Active Prompt Card
```
Border: 1px solid #2563eb
Background: rgba(37, 99, 235, 0.02)
```

### Badges

#### Active Badge
```
Background: rgba(16, 185, 129, 0.1)
Color: #10b981
Padding: 4px 10px
Border Radius: 12px
Font Size: 11px
Font Weight: 600
Text Transform: uppercase
```

#### Inactive Badge
```
Background: rgba(148, 163, 184, 0.1)
Color: #94a3b8
```

#### Step Badge
```
Background: rgba(37, 99, 235, 0.1)
Color: #2563eb
```

### Модальные окна

#### Modal Overlay
```
Background: rgba(0, 0, 0, 0.5)
Backdrop Filter: blur(4px)
Position: fixed, full screen
```

#### Modal Content
```
Background: white
Border Radius: 8px
Padding: 32px
Max Width: 600px
Width: 90%
Max Height: 90vh
Overflow: auto
Shadow: 0 10px 15px rgba(0,0,0,0.1)
```

#### Large Modal
```
Max Width: 900px
```

### Формы

#### Input Fields
```
Padding: 10px 12px
Border: 1px solid #e2e8f0
Border Radius: 4px
Font Size: 14px
Background: white
Focus: Border #2563eb, Shadow 0 0 0 3px rgba(37,99,235,0.1)
```

#### Textarea
```
Min Height: 100px
Resize: vertical
```

#### Error State
```
Border Color: #ef4444
```

### Toast Notifications

#### Toast Container
```
Position: fixed
Top: 20px
Right: 20px
Z-index: 10000
Display: flex column
Gap: 12px
```

#### Toast
```
Background: white
Border: 1px solid #e2e8f0
Border Radius: 8px
Padding: 16px 20px
Min Width: 300px
Max Width: 400px
Shadow: 0 10px 15px rgba(0,0,0,0.1)
Border Left: 4px solid (varies by type)
```

#### Toast Types
```
Success: Border Left #10b981
Error: Border Left #ef4444
Warning: Border Left #f59e0b
Info: Border Left #2563eb
```

### Tabs

#### Tab Button
```
Padding: 16px 24px
Background: transparent
Border: none
Border Bottom: 2px solid transparent
Font Size: 14px
Font Weight: 500
Color: #64748b
Active: Color #2563eb, Border Bottom #2563eb
Hover: Background #f8fafc, Color #1e293b
```

### History Items

#### History Card
```
Background: white
Border: 1px solid #e2e8f0
Border Left: 3px solid (varies)
Border Radius: 8px
Padding: 16px
Cursor: pointer
Hover: Border #2563eb, Shadow
```

#### Success History
```
Border Left: 3px solid #10b981
```

#### Error History
```
Border Left: 3px solid #ef4444
```

### JSON Viewer

#### JSON Container
```
Background: #f8fafc
Border: 1px solid #e2e8f0
Border Radius: 4px
Padding: 16px
Max Height: 400px
Overflow: auto
Font Family: Monaco, Menlo, Ubuntu Mono, monospace
Font Size: 12px
```

#### JSON Syntax Colors
```
Keys: #881391 (фиолетовый)
Strings: #0b7500 (зеленый)
Numbers: #1c00cf (синий)
Booleans: #0d22aa (синий)
Null: #808080 (серый)
```

## 📱 Responsive Breakpoints

```
Mobile: max-width 768px
Tablet: 768px - 1024px
Desktop: 1024px+
```

### Mobile Adaptations
```
- Single column layouts
- Reduced padding (20px → 16px)
- Stacked form elements
- Horizontal scroll for tabs
```

## 🎯 Тени

```
Small: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)
Medium: 0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)
Large: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)
```

## 🔄 Анимации

### Transitions
```
Duration: 0.2s
Easing: ease
Properties: all
```

### Keyframe Animations
```
Pulse: opacity 1 → 0.5 → 1 (2s infinite)
Slide In Right: translateX(100%) → translateX(0) (0.3s ease)
```

## 📋 Иконки

Используются эмодзи и Unicode символы:
- ✅ Success
- ❌ Error
- ⚠️ Warning
- ℹ️ Info
- 📋 Copy
- 🔍 Search

## 🎨 Состояния компонентов

### Hover States
- Кнопки: изменение цвета фона, легкий подъем (translateY)
- Карточки: изменение цвета границы, добавление тени
- Ссылки: подчеркивание, изменение цвета

### Focus States
- Input: синяя рамка, тень с синим оттенком
- Кнопки: outline с синим цветом

### Disabled States
- Opacity: 0.6
- Cursor: not-allowed
- Pointer events: none

## 📐 Layout Grid

### Container
```
Max Width: 1400px
Margin: 0 auto
Background: white
Min Height: 100vh
```

### Grid Systems
```
Prompts Grid: repeat(auto-fill, minmax(320px, 1fr))
Gap: 20px
```

## 🔗 Связи между компонентами

1. **Header** → Stats Bar → Stat Items
2. **Tabs** → Tab Content → Section Header → Content Grid/List
3. **Modal** → Modal Content → Form → Form Groups → Inputs
4. **Toast Container** → Toast → Toast Content
5. **History List** → History Items → History Details Modal

## 📝 Рекомендации для Figma

1. Создайте компоненты для всех перечисленных элементов
2. Используйте Auto Layout для адаптивности
3. Настройте Variants для состояний (hover, active, disabled)
4. Создайте Color Styles для всех цветов
5. Настройте Text Styles для типографики
6. Используйте Constraints для responsive дизайна
7. Создайте Component Library для переиспользования

## 🚀 Следующие шаги

1. Создайте новый файл в Figma
2. Импортируйте эту дизайн-систему
3. Создайте компоненты согласно спецификации
4. Постройте макеты страниц используя компоненты
5. Настройте прототипирование для интерактивности

