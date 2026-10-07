/**
 * Посещаемость: цвет → «был» / «н».
 *
 * Формулы не видят цвет заливки, поэтому скрипт один раз проходит по листу
 * «Посещаемость» и пишет текст в пустые ячейки под датами:
 *   зелёная заливка → «был», красная → «н».
 * Ячейки с текстом, числами и формулами не трогает, чёрные и белые пропускает.
 * Потом добавляет условное форматирование, чтобы новые отметки красились сами.
 *
 * Как запустить: Расширения → Apps Script → вставить код → Сохранить →
 * выбрать attendanceColorsToText → Выполнить → разрешить доступ.
 */
function attendanceColorsToText() {
  const sheet = SpreadsheetApp.getActive().getSheetByName('Посещаемость');
  if (!sheet) throw new Error('Не нашёл лист «Посещаемость»');
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 2) return;

  const header = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const range = sheet.getRange(2, 1, lastRow - 1, lastCol);
  const values = range.getValues();
  const formulas = range.getFormulas();
  const colors = range.getBackgrounds();

  let present = 0;
  let absent = 0;
  for (let r = 0; r < values.length; r++) {
    for (let c = 0; c < lastCol; c++) {
      if (formulas[r][c]) { values[r][c] = formulas[r][c]; continue; } // формулы сохраняем
      if (c === 0 || values[r][0] === '' || !isDateHeader(header[c])) continue; // имя, пустая строка, не дата
      if (values[r][c] !== '') continue;                                  // уже есть отметка
      const kind = colorKind(colors[r][c]);
      if (kind === 'green') { values[r][c] = 'был'; present++; }
      if (kind === 'red') { values[r][c] = 'н'; absent++; }
    }
  }
  range.setValues(values);

  const marks = sheet.getRange(2, 2, lastRow - 1, lastCol - 1);
  const rules = sheet.getConditionalFormatRules().filter(rule => { // при повторном запуске правила не дублируются
    const cond = rule.getBooleanCondition();
    const v = cond ? cond.getCriteriaValues()[0] : null;
    return !(cond && cond.getCriteriaType() === SpreadsheetApp.BooleanCriteria.TEXT_EQUAL_TO && (v === 'был' || v === 'н'));
  });
  rules.push(
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('был')
      .setBackground('#00ff00').setFontColor('#000000').setRanges([marks]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('н')
      .setBackground('#ff0000').setFontColor('#000000').setRanges([marks]).build()
  );
  sheet.setConditionalFormatRules(rules);

  SpreadsheetApp.getActive().toast('Готово: «был» — ' + present + ', «н» — ' + absent);
}

/** Дата в шапке: значение-дата или текст вроде «20.09 общее». */
function isDateHeader(h) {
  return Object.prototype.toString.call(h) === '[object Date]' || /^\s*\d{1,2}[.\/]\d{1,2}/.test(String(h));
}

/** Зелёный, красный или ни то ни другое — по оттенку заливки. */
function colorKind(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
  if (!m) return null;
  const n = parseInt(m[1], 16);
  const r = ((n >> 16) & 255) / 255;
  const g = ((n >> 8) & 255) / 255;
  const b = (n & 255) / 255;
  const max = Math.max(r, g, b);
  const d = max - Math.min(r, g, b);
  if (max < 0.25 || d / max < 0.12) return null; // почти чёрный, серый или белый
  let h;
  if (max === r) h = 60 * (((g - b) / d) % 6);
  else if (max === g) h = 60 * ((b - r) / d + 2);
  else h = 60 * ((r - g) / d + 4);
  if (h < 0) h += 360;
  if (h >= 75 && h <= 165) return 'green';
  if (h >= 340 || h <= 20) return 'red';
  return null;
}
