# Руководство по созданию UI в Figma

## 🎯 Цель
Создать полный дизайн UI для REESTRY на основе существующего кода и дизайн-системы.

## 📋 Пошаговый план

### Шаг 1: Настройка дизайн-системы

#### 1.1 Создайте Color Styles
В Figma: Right-click на цвете → "Add as style"

**Основные цвета:**
- `Primary`: #2563EB
- `Primary Hover`: #1D4ED8
- `Secondary`: #64748B
- `Success`: #10B981
- `Error`: #EF4444
- `Warning`: #F59E0B
- `Background`: #FFFFFF
- `Background Secondary`: #F8FAFC
- `Border`: #E2E8F0
- `Text Primary`: #1E293B
- `Text Secondary`: #64748B
- `Text Muted`: #94A3B8

#### 1.2 Создайте Text Styles
В Figma: Text → Style → Create style

**Заголовки:**
- `H1`: 24px, Weight 600, Color: Text Primary
- `H2`: 20px, Weight 600, Color: Text Primary
- `H3`: 16px, Weight 600, Color: Text Primary

**Текст:**
- `Body`: 14px, Weight 400, Color: Text Primary
- `Body Small`: 13px, Weight 400, Color: Text Secondary
- `Caption`: 12px, Weight 400, Color: Text Muted
- `Label`: 12px, Weight 500, Color: Text Muted, Uppercase

**Моноширинный:**
- `Code`: 12px, Weight 400, Font: Monaco/Menlo, Color: Text Primary

### Шаг 2: Создание компонентов

#### 2.1 Button Component

**Создайте Frame:**
- Width: Auto (с padding)
- Height: Auto
- Padding: 10px 20px
- Border Radius: 4px
- Background: Primary color

**Variants:**
1. **Primary**
   - Background: Primary
   - Text: White
   - Hover: Primary Hover

2. **Secondary**
   - Background: Background Secondary
   - Text: Text Primary
   - Border: 1px Border color

3. **Danger**
   - Background: Error
   - Text: White

4. **Small**
   - Padding: 6px 12px
   - Font Size: 12px

**States:**
- Default
- Hover (слегка поднят, тень)
- Disabled (opacity 60%)

#### 2.2 Card Component

**Создайте Frame:**
- Width: 320px (min)
- Padding: 20px
- Border: 1px Border color
- Border Radius: 8px
- Background: Background
- Shadow: Small shadow

**Variants:**
- Default
- Active (border Primary, background rgba(37, 99, 235, 0.02))
- Hover (border Primary, shadow Medium)

#### 2.3 Badge Component

**Создайте Frame:**
- Width: Auto
- Height: Auto
- Padding: 4px 10px
- Border Radius: 12px
- Font Size: 11px
- Font Weight: 600
- Text Transform: Uppercase

**Variants:**
- Active: Background rgba(16, 185, 129, 0.1), Color Success
- Inactive: Background rgba(148, 163, 184, 0.1), Color Text Muted
- Step: Background rgba(37, 99, 235, 0.1), Color Primary

#### 2.4 Input Component

**Создайте Frame:**
- Width: 100% (или фиксированная)
- Height: Auto
- Padding: 10px 12px
- Border: 1px Border color
- Border Radius: 4px
- Background: Background
- Font: Body

**States:**
- Default
- Focus (border Primary, shadow с Primary оттенком)
- Error (border Error)
- Disabled

#### 2.5 Modal Component

**Overlay:**
- Full screen
- Background: rgba(0, 0, 0, 0.5)
- Backdrop Filter: blur(4px)

**Content:**
- Width: 600px (max)
- Max Height: 90vh
- Padding: 32px
- Border Radius: 8px
- Background: Background
- Shadow: Large shadow
- Overflow: Auto

**Variants:**
- Default (600px)
- Large (900px)

#### 2.6 Toast Component

**Создайте Frame:**
- Width: 300-400px
- Padding: 16px 20px
- Border Radius: 8px
- Background: Background
- Border: 1px Border color
- Border Left: 4px (varies by type)
- Shadow: Large shadow

**Variants:**
- Success (border left Success)
- Error (border left Error)
- Warning (border left Warning)
- Info (border left Primary)

### Шаг 3: Создание страниц

#### 3.1 Главная страница - Промпты

**Layout:**
```
┌─────────────────────────────────────┐
│ Header (1400px max width)          │
│  - Title: REESTRY                  │
│  - Stats Bar (3 stat items)        │
├─────────────────────────────────────┤
│ Tabs Navigation                     │
│  [Промпты] [Датасеты] [История]... │
├─────────────────────────────────────┤
│ Section Header                      │
│  - Title: Управление промптами      │
│  - Search Box + Filters + Button    │
├─────────────────────────────────────┤
│ Prompts Grid (3 columns)           │
│  [Card] [Card] [Card]              │
│  [Card] [Card] [Card]              │
└─────────────────────────────────────┘
```

**Размеры:**
- Container: 1400px max width, centered
- Header padding: 24px 32px
- Section padding: 32px
- Grid gap: 20px
- Card min width: 320px

#### 3.2 Prompt Card Layout

```
┌─────────────────────────────┐
│ Prompt Name (16px, Bold)    │
│ [Active Badge] [Step Badge] │
├─────────────────────────────┤
│ Description (13px, Gray)    │
├─────────────────────────────┤
│ Meta: Temp | Max Tokens     │
├─────────────────────────────┤
│ [Edit] [Copy] [Delete]      │
└─────────────────────────────┘
```

#### 3.3 Modal - Create/Edit Prompt

```
┌─────────────────────────────────┐
│ ×  Create/Edit Prompt          │
├─────────────────────────────────┤
│ Name * [Input]                  │
│ Description [Textarea]          │
│ Algorithm Step * [Select]       │
│ System Prompt [Textarea]        │
│ User Template [Textarea]        │
│ Temperature | Max Tokens        │
│ [✓] Active                      │
├─────────────────────────────────┤
│        [Cancel] [Save]          │
└─────────────────────────────────┘
```

### Шаг 4: Детальные спецификации

#### Header Component
- **Height**: Auto (padding 24px 32px)
- **Background**: Background
- **Border Bottom**: 1px Border color
- **Title**: H1 style
- **Stats Bar**: Flex, gap 32px, wrap

#### Stats Bar Item
- **Layout**: Column
- **Gap**: 4px
- **Label**: Label style (12px, uppercase)
- **Value**: 20px, Weight 600

#### Tabs
- **Height**: Auto
- **Padding**: 0 32px
- **Border Bottom**: 1px Border color
- **Tab Button**: Padding 16px 24px, Border bottom 2px transparent
- **Active Tab**: Color Primary, Border bottom Primary

#### Search Box
- **Layout**: Flex row
- **Gap**: 8px
- **Input**: Min width 200px
- **Select**: Auto width

#### Prompt Card
- **Width**: Min 320px, flex grow
- **Padding**: 20px
- **Gap между элементами**: 12px
- **Actions**: Flex row, gap 8px

#### History Item
- **Padding**: 16px
- **Border Left**: 3px (Success/Error)
- **Layout**: Column
- **Gap**: 8px
- **Cursor**: Pointer

### Шаг 5: Responsive Design

#### Breakpoint: 768px

**Изменения:**
- Grid: 3 columns → 1 column
- Padding: 32px → 16px
- Header padding: 24px 32px → 20px 16px
- Tabs: Horizontal scroll
- Form: Stacked (column layout)

### Шаг 6: Auto Layout настройки

Для всех компонентов используйте Auto Layout:
- **Direction**: Column (для карточек, форм)
- **Direction**: Row (для кнопок, stats)
- **Padding**: Согласно спецификации
- **Gap**: Согласно спецификации
- **Constraints**: 
  - Container: Center horizontally
  - Cards: Fill container width
  - Buttons: Hug contents

### Шаг 7: Создание прототипа

#### Интерактивность:
1. **Tabs**: 
   - On Click → Navigate to page
   - Change active state

2. **Buttons**:
   - On Hover → Change to hover state
   - On Click → Show modal or action

3. **Cards**:
   - On Hover → Change to hover state
   - On Click → Show details

4. **Modal**:
   - Overlay click → Close modal
   - Close button → Close modal

### Шаг 8: Экспорт и подготовка

#### Для разработчиков:
1. Экспортируйте все иконки как SVG
2. Создайте Style Guide page с цветами и типографикой
3. Добавьте annotations для сложных компонентов
4. Экспортируйте assets в нужных размерах

#### Компоненты для экспорта:
- Все иконки (если есть)
- Логотип (если есть)
- Специальные изображения

## 🎨 Дополнительные рекомендации

### Используйте Constraints правильно:
- **Left/Right**: Left & Right для растягивания
- **Center**: Center для центрирования
- **Scale**: Scale для пропорционального изменения

### Организация файла:
```
Pages:
1. 🎨 Design System (цвета, типографика, компоненты)
2. 📱 Desktop (1400px)
3. 📱 Tablet (768px)
4. 📱 Mobile (375px)
5. 🧩 Components (библиотека компонентов)
6. 📋 Style Guide
```

### Naming Convention:
- Components: `Component/State` (Button/Primary, Card/Default)
- Pages: `Page Name` (Prompts, Datasets, History)
- Frames: `Section Name` (Header, Stats Bar, Content)

## 🚀 Быстрый старт

1. **Создайте Color Styles** (5 минут)
2. **Создайте Text Styles** (10 минут)
3. **Создайте Button Component** (15 минут)
4. **Создайте Card Component** (20 минут)
5. **Создайте главную страницу** (30 минут)
6. **Добавьте остальные страницы** (1 час)

**Общее время: ~2-3 часа**

## 📝 Checklist

- [ ] Color Styles созданы
- [ ] Text Styles созданы
- [ ] Button Component с variants
- [ ] Card Component с variants
- [ ] Badge Component с variants
- [ ] Input Component с states
- [ ] Modal Component
- [ ] Toast Component
- [ ] Header создан
- [ ] Tabs созданы
- [ ] Prompts page создана
- [ ] Datasets page создана
- [ ] History page создана
- [ ] Algorithm page создана
- [ ] Responsive версии созданы
- [ ] Прототип настроен
- [ ] Style Guide создан

## 💡 Советы

1. Используйте Auto Layout везде - это сэкономит время
2. Создавайте компоненты с variants сразу
3. Используйте Constraints для responsive
4. Группируйте связанные элементы в Frames
5. Называйте все элементы понятно
6. Используйте плагины для ускорения работы (например, Figma Tokens)

