'use strict';

var gulp = require('gulp');
var shell = require('gulp-shell');
var connect = require('gulp-connect');
var sass = require('gulp-sass');

gulp.task('sphinx', shell.task('sphinx-build docs docs/build/html'));

//gulp.task('docs', ['build-docs'], function() {
//  gulp.watch(['./docs/**/*.rst', './docs/**/*.py', './docs/**/*.conf'], ['build-docs']);
//});

gulp.task('sass', function () {
  return gulp.src('./docs/_theme/react/styles/**/*.scss')
    .pipe(sass().on('error', sass.logError))
    .pipe(gulp.dest('./docs/_theme/react/static/'));
});

gulp.task('connect', function() {
  connect.server({
    root: 'docs/build/html',
    livereload: true
  });
});

 gulp.task('watch', function () {
   gulp.watch(['./docs/**/*.rst', './docs/**/*.py', './docs/**/*.conf'], ['sphinx']);
   gulp.watch('./sass/**/*.scss', ['sass']);
 });

gulp.task('default', ['connect', 'watch']);




