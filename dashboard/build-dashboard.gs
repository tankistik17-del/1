/**
 * Сводка для таблицы репетитора.
 *
 * setupDashboard() создаёт листы «Сводка» и «Ученик» со всеми формулами,
 * оформлением и графиком, а перед этим переводит цветные отметки на листе
 * «Посещаемость» в «был» / «н» (иначе формулы их не видят).
 * Старые листы скрипт не меняет, кроме пустых ячеек посещаемости.
 *
 * Как запустить (на компьютере):
 *   Расширения → Apps Script → удалить всё в редакторе → вставить этот код →
 *   Сохранить → вверху выбрать setupDashboard → Выполнить → разрешить доступ.
 */
const SUMMARY = 'Сводка';
const CARD = 'Ученик';
const SOURCES = ['Посещаемость', 'Успеваемость', 'Пробники', 'КЭС'];
const F = {
  title: "=\"Учеников: \" & COUNTA(B15:B44) & \" · обновлено \" & TEXT(TODAY(); \"dd.mm.yyyy\")",
  t_att: "=LET( n_ok; COUNTIF('Посещаемость'!$2:$100; \"был\"); n_miss; COUNTIF('Посещаемость'!$2:$100; \"н\"); IFERROR(n_ok / (n_ok + n_miss); \"—\") )",
  t_att_trend: "=SPARKLINE(S15:S60; {\"charttype\"\\\"line\"; \"ymin\"\\0; \"ymax\"\\1; \"empty\"\\\"ignore\"; \"color\"\\\"#2A78D6\"; \"linewidth\"\\2})",
  t_hw: "=IFERROR(SUM(N15:N44) / SUM(O15:O44); \"—\")",
  t_tests: "=IFERROR(AVERAGE(G15:G44); \"—\")",
  t_mock: "=IFERROR(AVERAGE(I15:I44); \"—\")",
  t_kes: "=COUNTIF(INDEX('КЭС'!$1:$100; 0; MATCH(\"Довели до 1 дз\"; 'КЭС'!$1:$1; 0)); 1)",
  t_risk: "=COUNTIF(A15:A44; \"риск\")",
  a_att: "=IFERROR(TEXTJOIN(\", \"; TRUE; FILTER(B15:B44 & \" (\" & TEXT(E15:E44; \"0%\") & \")\"; E15:E44 <> \"\"; E15:E44 < 70%) ); \"—\")",
  a_streak: "=IFERROR(TEXTJOIN(\", \"; TRUE; FILTER(B15:B44 & \" (\" & M15:M44 & \")\"; M15:M44 <> \"\"; M15:M44 >= 2) ); \"—\")",
  a_hw: "=IFERROR(TEXTJOIN(\", \"; TRUE; FILTER(B15:B44; O15:O44 <> \"\"; O15:O44 >= 2; N15:N44 = 0) ); \"—\")",
  a_mock: "=IFERROR(TEXTJOIN(\", \"; TRUE; FILTER(B15:B44; B15:B44 <> \"\"; I15:I44 = \"\") ); \"—\")",
  a_star: "=IFERROR(TEXTJOIN(\", \"; TRUE; FILTER(B15:B44; E15:E44 = 1; P15:P44 = 1) ); \"—\")",
  c_name: "=FILTER('Посещаемость'!A2:A40; 'Посещаемость'!A2:A40 <> \"\")",
  c_status: "=IF($B15 = \"\"; \"\"; IFS( AND(E15 <> \"\"; E15 < 70%); \"риск\"; AND(M15 <> \"\"; M15 >= 2); \"риск\"; AND(N(O15) >= 2; N(N15) = 0); \"риск\"; AND(E15 <> \"\"; E15 < 90%); \"внимание\"; AND(P15 <> \"\"; P15 < 50%); \"внимание\"; I15 = \"\"; \"внимание\"; TRUE; \"норм\" ))",
  c_goal: "=IF($B15 = \"\"; \"\"; IFERROR(REGEXEXTRACT( INDEX('Успеваемость'!$A:$A; MATCH($B15 & \"*\"; 'Успеваемость'!$A:$A; 0)); \"\\((.+)\\)\"); \"—\"))",
  c_spark: "=IF($B15 = \"\"; \"\"; IFERROR(LET( a_head; 'Посещаемость'!$1:$1; a_row; INDEX('Посещаемость'!$1:$100; MATCH($B15; 'Посещаемость'!$A$1:$A$100; 0); 0); a_marks; FILTER(a_row; COLUMN(a_head) > 1; a_head <> \"\"); SPARKLINE(ARRAYFORMULA(IF(a_marks = \"был\"; 1; IF(a_marks = \"н\"; -1; 0))); {\"charttype\"\\\"winloss\"; \"color\"\\\"#0CA30C\"; \"negcolor\"\\\"#D03B3B\"}) ); \"\"))",
  c_att: "=IF($B15 = \"\"; \"\"; IFERROR(LET( a_row; INDEX('Посещаемость'!$1:$100; MATCH($B15; 'Посещаемость'!$A$1:$A$100; 0); 0); n_ok; COUNTIF(a_row; \"был\"); n_miss; COUNTIF(a_row; \"н\"); IF(n_ok + n_miss = 0; \"\"; n_ok / (n_ok + n_miss)) ); \"\"))",
  c_hwtext: "=IF(OR($B15 = \"\"; O15 = \"\"); \"\"; N15 & \" из \" & O15)",
  c_tests: "=IF($B15 = \"\"; \"\"; IFERROR(LET( u_head; 'Успеваемость'!$2:$2; u_row; INDEX('Успеваемость'!$1:$100; MATCH($B15 & \"*\"; 'Успеваемость'!$A$1:$A$100; 0); 0); is_test; ARRAYFORMULA(REGEXMATCH(u_head & \"\"; \"(?i)правильн\") * ISNUMBER(u_row)); t_max; ARRAYFORMULA(IFERROR(VALUE(REGEXEXTRACT(u_head & \"\"; \"макс\\s*(\\d+)\")); 0)); t_got; ARRAYFORMULA(IFERROR(u_row * 1; 0)); SUMPRODUCT(is_test; t_got) / SUMPRODUCT(is_test; t_max) ); \"\"))",
  c_notes: "=IF($B15 = \"\"; \"\"; IFERROR(LET( u_head; 'Успеваемость'!$2:$2; u_row; INDEX('Успеваемость'!$1:$100; MATCH($B15 & \"*\"; 'Успеваемость'!$A$1:$A$100; 0); 0); k_ok; COUNTIFS(u_head; \"*конспект*\"; u_row; \"прислал*\"); k_all; COUNTIFS(u_head; \"*конспект*\"; u_row; \"*прислал*\"); IF(k_all = 0; \"\"; k_ok / k_all) ); \"\"))",
  c_mock: "=IF($B15 = \"\"; \"\"; IFERROR(INDEX('Пробники'!$C:$C; MATCH($B15; 'Пробники'!$A:$A; 0)); \"\"))",
  c_kes: "=IF($B15 = \"\"; \"\"; IFERROR(LET( k_head; 'КЭС'!$1:$1; k_row; INDEX('КЭС'!$1:$100; MATCH($B15; 'КЭС'!$B$1:$B$100; 0); 0); n_done; COUNTIFS(k_head; \"Довели*\"; k_row; 1); n_all; COUNTIF(k_head; \"Довели*\"); REPT(\"●\"; n_done) & REPT(\"○\"; n_all - n_done) ); \"нет в КЭС\"))",
  c_tg: "=IF($B15 = \"\"; \"\"; LET( nick; IFERROR(INDEX('КЭС'!$A:$A; MATCH($B15; 'КЭС'!$B:$B; 0)); \"\"); IF(nick = \"\"; \"—\"; HYPERLINK(\"https://t.me/\" & SUBSTITUTE(nick; \"@\"; \"\"); \"написать \" & nick)) ))",
  h_streak: "=IF($B15 = \"\"; \"\"; IFERROR(LET( a_head; 'Посещаемость'!$1:$1; a_row; INDEX('Посещаемость'!$1:$100; MATCH($B15; 'Посещаемость'!$A$1:$A$100; 0); 0); a_marks; FILTER(a_row; COLUMN(a_head) > 1; (a_row = \"был\") + (a_row = \"н\") > 0); COLUMNS(a_marks) - IFERROR(XMATCH(\"был\"; a_marks; 0; -1); 0) ); \"\"))",
  h_hwok: "=IF($B15 = \"\"; \"\"; IFERROR(LET( u_head; 'Успеваемость'!$2:$2; u_row; INDEX('Успеваемость'!$1:$100; MATCH($B15 & \"*\"; 'Успеваемость'!$A$1:$A$100; 0); 0); SUMPRODUCT(ARRAYFORMULA(REGEXMATCH(u_head & \"\"; \"(?i)^\\s*дз\") * ISNUMBER(u_row))) ); \"\"))",
  h_hwall: "=IF($B15 = \"\"; \"\"; IFERROR(LET( u_head; 'Успеваемость'!$2:$2; u_row; INDEX('Успеваемость'!$1:$100; MATCH($B15 & \"*\"; 'Успеваемость'!$A$1:$A$100; 0); 0); SUMPRODUCT(ARRAYFORMULA(REGEXMATCH(u_head & \"\"; \"(?i)^\\s*дз\") * (1 - REGEXMATCH(u_row & \"\"; \"^\\s*[-—–]\\s*$\")))) ); \"\"))",
  h_hwpct: "=IF(OR($B15 = \"\"; N(O15) = 0); \"\"; N15 / O15)",
  s_att: "=LET( a_head; 'Посещаемость'!$1:$1; a_data; 'Посещаемость'!$2:$100; n_ok; BYCOL(a_data; LAMBDA(c_col; COUNTIF(c_col; \"был\"))); n_miss; BYCOL(a_data; LAMBDA(c_col; COUNTIF(c_col; \"н\"))); TRANSPOSE(FILTER( VSTACK(a_head; ARRAYFORMULA(IFERROR(n_ok / (n_ok + n_miss); \"\"))); COLUMN(a_head) > 1; a_head <> \"\"; ARRAYFORMULA(n_ok + n_miss > 0))) )",
  s_kes: "=LET( k_head; 'КЭС'!$1:$1; k_data; 'КЭС'!$2:$100; n_yes; BYCOL(k_data; LAMBDA(c_col; COUNTIF(c_col; 1))); TRANSPOSE(FILTER( VSTACK(ARRAYFORMULA(SUBSTITUTE(k_head & \"\"; \"Довели до \"; \"\")); n_yes); ARRAYFORMULA(REGEXMATCH(k_head & \"\"; \"^Довели\")))) )",
  s_kesbar: "=IF(V15 = \"\"; \"\"; SPARKLINE(V15; {\"charttype\"\\\"bar\"; \"max\"\\COUNTA($B$15:$B$44); \"color1\"\\\"#2A78D6\"}))",
  s_mock: "=IFERROR(SORT(FILTER(HSTACK(B15:B44; I15:I44; C15:C44); ISNUMBER(I15:I44)); 2; FALSE); \"\")",
  s_grade: "=IF(Z15 = \"\"; \"\"; IFS(Z15 >= 22; 5; Z15 >= 15; 4; Z15 >= 8; 3; TRUE; 2))",
  s_bar: "=IF(Z15 = \"\"; \"\"; SPARKLINE(Z15; {\"charttype\"\\\"bar\"; \"max\"\\31; \"color1\"\\IF(AB15 >= 4; \"#0CA30C\"; IF(AB15 = 3; \"#FAB219\"; \"#D03B3B\"))}))",
  s_gap: "=IF(OR(Z15 = \"\"; AA15 = \"\"; AA15 = \"—\"); \"\"; LET( goal_n; VALUE(LEFT(AA15)); need_n; IFS(goal_n >= 5; 22; goal_n = 4; 15; TRUE; 8); IF(Z15 >= need_n; \"цель есть\"; \"не хватает \" & (need_n - Z15)) ))",
  s_bday: "=LET( d_name; 'ДР'!A2:A; d_date; 'ДР'!B2:B; d_left; ARRAYFORMULA(IF(ISNUMBER(d_date); MOD(DATE(YEAR(TODAY()); MONTH(d_date); DAY(d_date)) - TODAY(); 365); \"\")); IFERROR(SORT(FILTER(HSTACK(d_name; ARRAYFORMULA(TEXT(d_date; \"dd.mm\")); d_left); d_left <> \"\"; d_left <= 14); 3; TRUE); \"в ближайшие 2 недели — нет\") )",
  k_stats: "=XLOOKUP($B$2; 'Сводка'!$B$15:$B$44; 'Сводка'!$A$15:$A$44; \"\")",
  k_dates: "=FILTER('Посещаемость'!$1:$1; COLUMN('Посещаемость'!$1:$1) > 1; 'Посещаемость'!$1:$1 <> \"\")",
  k_marks: "=LET( a_head; 'Посещаемость'!$1:$1; a_row; INDEX('Посещаемость'!$1:$100; MATCH($B$2; 'Посещаемость'!$A$1:$A$100; 0); 0); FILTER(a_row; COLUMN(a_head) > 1; a_head <> \"\") )",
  k_msg: "=LET( s_name; $B$2; a_head; 'Посещаемость'!$1:$1; a_row; INDEX('Посещаемость'!$1:$100; MATCH(s_name; 'Посещаемость'!$A$1:$A$100; 0); 0); n_ok; COUNTIF(a_row; \"был\"); n_miss; COUNTIF(a_row; \"н\"); missed; IFERROR(TEXTJOIN(\", \"; TRUE; ARRAYFORMULA(TEXT(FILTER(a_head; a_row = \"н\"); \"dd.mm\"))); \"\"); hw_ok; N(XLOOKUP(s_name; 'Сводка'!$B$15:$B$44; 'Сводка'!$N$15:$N$44; 0)); hw_all; N(XLOOKUP(s_name; 'Сводка'!$B$15:$B$44; 'Сводка'!$O$15:$O$44; 0)); tests; XLOOKUP(s_name; 'Сводка'!$B$15:$B$44; 'Сводка'!$G$15:$G$44; \"\"); mock; XLOOKUP(s_name; 'Сводка'!$B$15:$B$44; 'Сводка'!$I$15:$I$44; \"\"); \"Добрый день! Итоги на \" & TEXT(TODAY(); \"dd.mm\") & \" — \" & s_name & \":\" & CHAR(10) & \"• посещаемость: \" & n_ok & \" из \" & (n_ok + n_miss) & \" занятий\" & IF(n_miss > 0; \" (пропуски: \" & missed & \")\"; \"\") & CHAR(10) & \"• домашние задания: сдано \" & hw_ok & \" из \" & hw_all & CHAR(10) & IF(tests = \"\"; \"\"; \"• тесты на занятиях: в среднем \" & TEXT(tests; \"0%\") & CHAR(10)) & \"• входной пробник: \" & IF(mock = \"\"; \"ещё не написан\"; mock & \" б.\") & CHAR(10) & CHAR(10) & IFS( n_miss >= 2; \"Обратите, пожалуйста, внимание на пропуски — без занятий сложно держать темп.\"; hw_ok < hw_all / 2; \"Сейчас главное — сдать долги по ДЗ, я помогу составить план.\"; mock = \"\"; \"Ближайшая задача — написать входной пробник.\"; TRUE; \"Всё идёт хорошо, продолжаем в том же темпе!\" ) )",
  k_kes: "=IFERROR(LET( k_head; 'КЭС'!$1:$1; k_row; INDEX('КЭС'!$1:$100; MATCH($B$2; 'КЭС'!$B$1:$B$100; 0); 0); TRANSPOSE(FILTER( VSTACK(ARRAYFORMULA(SUBSTITUTE(k_head & \"\"; \"Довели до \"; \"\")); ARRAYFORMULA(IF(k_row = 1; \"✓\"; \"—\"))); ARRAYFORMULA(REGEXMATCH(k_head & \"\"; \"^Довели\")))) ); \"нет в КЭС\")",
  k_mocks: "=IFERROR(LET( p_head; 'Пробники'!$C$2:$M$2; p_row; INDEX('Пробники'!$C$1:$M$100; MATCH($B$2; 'Пробники'!$A$1:$A$100; 0); 0); TRANSPOSE(FILTER(VSTACK(p_head; p_row); ARRAYFORMULA(ISNUMBER(p_row)))) ); \"пробников пока нет\")",
  k_tasks: "=IFERROR(LET( u_week; 'Успеваемость'!$1:$1; u_head; 'Успеваемость'!$2:$2; u_row; INDEX('Успеваемость'!$1:$100; MATCH($B$2 & \"*\"; 'Успеваемость'!$A$1:$A$100; 0); 0); u_weeks; SCAN(\"\"; u_week; LAMBDA(acc; x; IF(x = \"\"; acc; x))); TRANSPOSE(FILTER( VSTACK(u_weeks; u_head; ARRAYFORMULA(IF(u_row = \"\"; \"не сдано\"; u_row))); COLUMN(u_head) > 1; u_head <> \"\")) ); \"\")",
}; // формулы в записи для русской локали: «;» между аргументами, «\» между столбцами в {…}
const RED = ['#fbe2e0', '#8e1c1c'];
const YELLOW = ['#fdf1d3', '#6a4700'];
const GREEN = ['#dff3df', '#135c13'];
const GRAY = '#5f6368';
const HEAD_BG = '#f1f3f4';

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Сводка')
    .addItem('Собрать листы «Сводка» и «Ученик»', 'setupDashboard')
    .addItem('Перевести цвета посещаемости в «был / н»', 'attendanceColorsToText')
    .addToUi();
}

function setupDashboard() {
  const ss = SpreadsheetApp.getActive();
  SOURCES.forEach(name => {
    if (!ss.getSheetByName(name)) throw new Error('Не нашёл лист «' + name + '». Проверь, что он называется именно так.');
  });
  [SUMMARY, CARD].forEach(name => {
    if (ss.getSheetByName(name)) throw new Error('Лист «' + name + '» уже есть. Переименуй или удали его и запусти снова.');
  });
  const marks = attendanceColorsToText();
  const summary = ss.insertSheet(SUMMARY, 0);
  const fx = formulaSyntax_(summary);
  buildSummary_(ss, summary, fx);
  const card = ss.insertSheet(CARD, 1);
  buildCard_(ss, summary, card, fx);
  ss.setActiveSheet(summary);
  ss.toast('Листы «Сводка» и «Ученик» готовы. Посещаемость: «был» — ' + marks.present + ', «н» — ' + marks.absent + '.', 'Сводка', 10);
}

/** Пробная формула: понимает ли таблица запись через запятую. Если да — переводим «;» и «\» в неё. */
function formulaSyntax_(sheet) {
  const cell = sheet.getRange('A1');
  cell.setFormula('=IF(TRUE,1,2)');
  SpreadsheetApp.flush();
  const commas = cell.getValue() === 1;
  cell.clearContent();
  return commas ? toCommaSyntax_ : f => f;
}

function toCommaSyntax_(f) {
  let out = '';
  let inStr = false;
  let inSheet = false;
  const stack = [];
  for (let i = 0; i < f.length; i++) {
    const ch = f[i];
    if (inStr) { out += ch; if (ch === '"') inStr = false; continue; }
    if (inSheet) { out += ch; if (ch === "'") inSheet = false; continue; }
    if (ch === '"') { inStr = true; out += ch; continue; }
    if (ch === "'") { inSheet = true; out += ch; continue; }
    if (ch === '(' || ch === '{') stack.push(ch);
    if (ch === ')' || ch === '}') stack.pop();
    const inBraces = stack[stack.length - 1] === '{';
    if (ch === ';' && !inBraces) { out += ','; continue; }
    if (ch === '\\' && inBraces) { out += ','; continue; }
    out += ch;
  }
  return out;
}

function buildSummary_(ss, sh, fx) {
  ensureColumns_(sh, 34);
  const put = (a1, f) => sh.getRange(a1).setFormula(fx(f));
  sh.getRange('A1').setValue('Сводка группы').setFontSize(16).setFontWeight('bold');
  put('A2', F.title);
  sh.getRange('A2').setFontColor(GRAY);

  const tiles = [
    ['A', 'Посещаемость', F.t_att, F.t_att_trend, '0%'],
    ['C', 'ДЗ сдано', F.t_hw, '=SUM(N15:N44) & " из " & SUM(O15:O44) & " сдано"', '0%'],
    ['E', 'Тесты, средний %', F.t_tests, '="учеников с тестами: " & COUNT(G15:G44)', '0%'],
    ['G', 'Входной пробник', F.t_mock, '="писали " & COUNT(I15:I44) & " из " & COUNTA(B15:B44)', '0.0'],
    ['I', 'Дошли до 1-го ДЗ', F.t_kes, '="из " & COUNTA(B15:B44)', '0'],
    ['K', 'В зоне риска', F.t_risk, '="внимание " & COUNTIF(A15:A44; "внимание") & " · норм " & COUNTIF(A15:A44; "норм")', '0'],
  ];
  tiles.forEach(([col, label, value, note, numberFormat]) => {
    const next = String.fromCharCode(col.charCodeAt(0) + 1);
    sh.getRange(col + '3').setValue(label).setFontSize(9).setFontColor(GRAY);
    sh.getRange(col + '4').setFormula(fx(value)).setFontSize(20).setFontWeight('bold').setNumberFormat(numberFormat).setHorizontalAlignment('left');
    sh.getRange(col + '5').setFormula(fx(note)).setFontSize(9).setFontColor(GRAY);
    [3, 4, 5].forEach(r => sh.getRange(col + r + ':' + next + r).merge());
    sh.getRange(col + '3:' + next + '5').setBorder(true, true, true, true, null, null, '#dadce0', SpreadsheetApp.BorderStyle.SOLID);
  });

  sh.getRange('A7').setValue('Требует внимания').setFontWeight('bold').setFontSize(12);
  [
    ['Посещаемость ниже 70%', F.a_att],
    ['Пропадают: 2+ пропуска подряд', F.a_streak],
    ['Не сдали ни одного ДЗ', F.a_hw],
    ['Не писали входной пробник', F.a_mock],
    ['Молодцы: все занятия и все ДЗ', F.a_star],
  ].forEach(([label, f], i) => {
    const r = 8 + i;
    sh.getRange('A' + r).setValue(label).setFontWeight('bold');
    sh.getRange('C' + r).setFormula(fx(f));
    sh.getRange('A' + r + ':B' + r).merge().setVerticalAlignment('top');
    sh.getRange('C' + r + ':K' + r).merge().setWrap(true).setVerticalAlignment('top');
  });

  const head = ['Статус', 'Ученик', 'Цель', 'Посещения', '%', 'ДЗ', 'Тесты', 'Конспекты', 'Входной', 'КЭС', 'Telegram', '', 'Подряд', 'ДЗ сдано', 'ДЗ задано', 'ДЗ %'];
  sh.getRange(14, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground(HEAD_BG);
  const row = { A: F.c_status, C: F.c_goal, D: F.c_spark, E: F.c_att, F: F.c_hwtext, G: F.c_tests, H: F.c_notes, I: F.c_mock, J: F.c_kes, K: F.c_tg, M: F.h_streak, N: F.h_hwok, O: F.h_hwall, P: F.h_hwpct };
  Object.keys(row).forEach(col => put(col + '15', row[col]));
  put('B15', F.c_name);
  [['A', 'A'], ['C', 'K'], ['M', 'P']].forEach(([c1, c2]) => sh.getRange(c1 + '15:' + c2 + '15').copyTo(sh.getRange(c1 + '16:' + c2 + '44')));
  ['E15:E44', 'G15:H44', 'P15:P44'].forEach(a1 => sh.getRange(a1).setNumberFormat('0%'));
  sh.getRange('A15:K44').setVerticalAlignment('middle');

  sh.getRange('R13').setValue('Посещаемость по занятиям').setFontWeight('bold');
  sh.getRange('R14:S14').setValues([['Занятие', 'Посещаемость']]).setFontWeight('bold').setBackground(HEAD_BG);
  put('R15', F.s_att);
  sh.getRange('R15:R60').setNumberFormat('dd.mm');
  sh.getRange('S15:S60').setNumberFormat('0%');

  sh.getRange('U13').setValue('КЭС: довели до…').setFontWeight('bold');
  sh.getRange('U14:W14').setValues([['Шаг', 'Учеников', '']]).setFontWeight('bold').setBackground(HEAD_BG);
  put('U15', F.s_kes);
  put('W15', F.s_kesbar);
  sh.getRange('W15').copyTo(sh.getRange('W16:W30'));

  sh.getRange('Y13').setValue('Входной пробник').setFontWeight('bold');
  sh.getRange('Y14:AD14').setValues([['Ученик', 'Балл', 'Цель', 'Оценка', '', 'До цели']]).setFontWeight('bold').setBackground(HEAD_BG);
  put('Y15', F.s_mock);
  put('AB15', F.s_grade);
  put('AC15', F.s_bar);
  put('AD15', F.s_gap);
  sh.getRange('AB15:AD15').copyTo(sh.getRange('AB16:AD44'));

  if (ss.getSheetByName('ДР')) {
    sh.getRange('AF13').setValue('Дни рождения: 2 недели').setFontWeight('bold');
    sh.getRange('AF14:AH14').setValues([['Ученик', 'Дата', 'Через, дн.']]).setFontWeight('bold').setBackground(HEAD_BG);
    put('AF15', F.s_bday);
  }

  const widths = { A: 90, B: 170, C: 50, D: 110, E: 60, F: 80, G: 70, H: 85, I: 70, J: 90, K: 170, L: 24, Q: 24, R: 110, S: 100, T: 24, U: 150, V: 80, W: 120, X: 24, Y: 160, Z: 50, AA: 50, AB: 60, AC: 120, AD: 110, AE: 24, AF: 160, AG: 60, AH: 80 };
  Object.keys(widths).forEach(c => sh.setColumnWidth(colIndex_(c), widths[c]));
  sh.hideColumns(13, 4);
  sh.setFrozenColumns(2);

  sh.setConditionalFormatRules([
    textRule_(sh, 'A15:A44', 'риск', RED),
    textRule_(sh, 'A15:A44', 'внимание', YELLOW),
    textRule_(sh, 'A15:A44', 'норм', GREEN),
    formulaRule_(sh, 'E15:E44', fx('=AND($E15<>""; $E15<70%)'), RED),
    formulaRule_(sh, 'E15:E44', fx('=AND($E15<>""; $E15<90%)'), YELLOW),
    formulaRule_(sh, 'F15:F44', fx('=AND(N($O15)>=2; N($N15)=0)'), RED),
    formulaRule_(sh, 'F15:F44', fx('=AND($P15<>""; $P15<50%)'), YELLOW),
    formulaRule_(sh, 'I15:I44', fx('=AND($B15<>""; $I15="")'), YELLOW),
  ]);

  sh.insertChart(sh.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .addRange(sh.getRange('R14:S40'))
    .setNumHeaders(1)
    .setPosition(46, 1, 0, 0)
    .setOption('title', 'Посещаемость по занятиям')
    .setOption('legend', { position: 'none' })
    .setOption('colors', ['#2a78d6'])
    .setOption('width', 640)
    .setOption('height', 300)
    .build());
}

function buildCard_(ss, summary, sh, fx) {
  sh.getRange('A1').setValue('Карточка ученика').setFontSize(16).setFontWeight('bold');
  sh.getRange('A2').setValue('Ученик').setFontWeight('bold');
  const pick = sh.getRange('B2');
  pick.setDataValidation(SpreadsheetApp.newDataValidation().requireValueInRange(summary.getRange('B15:B44'), true).setAllowInvalid(false).build());
  const first = ss.getSheetByName('Посещаемость').getRange('A2').getValue();
  if (first) pick.setValue(first);
  pick.setFontWeight('bold').setFontSize(12);

  sh.getRange('A4:I4').setValues([['Статус', 'Цель', 'Посещаемость', 'ДЗ', 'Тесты', 'Конспекты', 'Входной', 'КЭС', 'Telegram']]).setFontSize(9).setFontColor(GRAY);
  ['A', 'C', 'E', 'F', 'G', 'H', 'I', 'J'].forEach((c, i) => {
    sh.getRange(5, i + 1).setFormula(fx(F.k_stats.split("'Сводка'!$A$15:$A$44").join("'Сводка'!$" + c + '$15:$' + c + '$44')));
  });
  sh.getRange('I5').setFormula(fx(F.c_tg.split('$B15').join('$B$2')));
  sh.getRange('A5:I5').setFontWeight('bold').setFontSize(12);
  ['C5', 'E5:F5'].forEach(a1 => sh.getRange(a1).setNumberFormat('0%'));

  sh.getRange('A7').setValue('Даты').setFontWeight('bold');
  sh.getRange('B7').setFormula(fx(F.k_dates));
  sh.getRange('B7:Z7').setNumberFormat('dd.mm');
  sh.getRange('A8').setValue('Отметки').setFontWeight('bold');
  sh.getRange('B8').setFormula(fx(F.k_marks));

  sh.getRange('A10').setValue('Сообщение родителям').setFontWeight('bold').setFontSize(12);
  sh.getRange('A11').setFormula(fx(F.k_msg));
  sh.getRange('A11:I11').merge().setWrap(true).setVerticalAlignment('top');
  sh.setRowHeight(11, 170);

  sh.getRange('A13').setValue('КЭС').setFontWeight('bold').setFontSize(12);
  sh.getRange('A14').setFormula(fx(F.k_kes));
  sh.getRange('D13').setValue('Пробники').setFontWeight('bold').setFontSize(12);
  sh.getRange('D14').setFormula(fx(F.k_mocks));
  sh.getRange('A26').setValue('Все задания').setFontWeight('bold').setFontSize(12);
  sh.getRange('A27').setFormula(fx(F.k_tasks));

  const widths = { A: 150, B: 170, C: 110, D: 150, E: 90, F: 90, G: 90, H: 100, I: 170 };
  Object.keys(widths).forEach(c => sh.setColumnWidth(colIndex_(c), widths[c]));
  sh.setConditionalFormatRules([
    textRule_(sh, 'B8:Z8', 'был', GREEN),
    textRule_(sh, 'B8:Z8', 'н', RED),
    textRule_(sh, 'C27:C300', 'не сдано', RED),
  ]);
}

function textRule_(sh, a1, text, colors) {
  return SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(text)
    .setBackground(colors[0]).setFontColor(colors[1]).setRanges([sh.getRange(a1)]).build();
}

function formulaRule_(sh, a1, formula, colors) {
  return SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied(formula)
    .setBackground(colors[0]).setFontColor(colors[1]).setRanges([sh.getRange(a1)]).build();
}

function ensureColumns_(sh, n) {
  const have = sh.getMaxColumns();
  if (have < n) sh.insertColumnsAfter(have, n - have);
}

function colIndex_(letters) {
  return letters.split('').reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0);
}

/** Посещаемость: зелёная заливка → «был», красная → «н». Только пустые ячейки под датами. */
function attendanceColorsToText() {
  const sheet = SpreadsheetApp.getActive().getSheetByName('Посещаемость');
  if (!sheet) throw new Error('Не нашёл лист «Посещаемость»');
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 2) return { present: 0, absent: 0 };

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
  return { present, absent };
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
