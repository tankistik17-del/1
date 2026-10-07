// Builds stats.html: the page template with parser.js inlined. Run: node build.cjs
const fs = require('fs');
const tpl = fs.readFileSync(__dirname + '/app.tpl.html', 'utf8');
const parser = fs.readFileSync(__dirname + '/parser.js', 'utf8');
if (/<\/script/i.test(parser)) throw new Error('parser contains </script');
fs.writeFileSync(__dirname + '/stats.html', tpl.replace('/*__PARSER__*/', () => parser));
console.log('built', fs.statSync(__dirname + '/stats.html').size);
