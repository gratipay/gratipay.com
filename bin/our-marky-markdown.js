#!/usr/bin/env node
// Extend marky-markdown.js to support the package argument:
//  https://www.npmjs.com/package/marky-markdown#npm-packages

var fs = require('fs')
var path = require('path')
var marky = require('marky-markdown')

if (process.argv.length < 3) {
  console.log('Usage:\n\nour-marky-markdown some.md pkg > some.html')
  process.exit()
}

var filePath = path.resolve(process.cwd(), process.argv[2])

fs.readFile(filePath, function (err, data) {
  if (err) throw err
  var package =  process.argv[3] ? JSON.parse(process.argv[3]) : null;
  var html = marky(data.toString(), {package: package})
  process.stdout.write(html)
})
