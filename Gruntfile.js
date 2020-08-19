const sass = require("node-sass");

module.exports = function(grunt) {
  grunt.initConfig({
    pkg: grunt.file.readJSON("package.json"),
    scsslint: {
      dist: {
        allFiles: [
          "app/static/sass/*.scss",
        ],
        options: {
          bundleExec: false,
          colorizeOutput: true,
          compact: true,
          reporterOutput: null,
          maxBuffer: 3000 * 1024
        }
      },
    },
    sass: {
      options: {
        implementation: sass,
        sourceMap: true
      },
      dist: {
        options: {
          sourcemap: false,
          outputStyle: "compressed"
        },
        files: {
          "app/static/css/main.css": "app/sass/style.scss"
        }
      },
    },
    autoprefixer:{
      dist: {
        options: {
          browsers: ["last 2 versions", "> 1%"]
        },
        files:{
          "app/static/css/main.css": "app/static/css/main.css"
        }
      }
    },
    jslint: { // configure the task
      // lint your project"s client code
      client: {
        src: [
          "app/static/js/main.js",
          "app/static/js/map.js"
        ],
        directives: {
          browser: true,
          predef: [
            "$",
            "jQuery",
            "console"
          ]
        },
      }
    },
/*    uglify: {
      themejs: {
        files: {
          "js/main.min.js": ["js/main.js"]
        }
      }
    },*/
    watch: {
      css: {
        files: "app/sass/**/*.scss",
        tasks: ["sass"]
      },
      js: {
        files: "app/static/js/**/*.js",
        tasks: ["jslint", "uglify"]
      }
    },
    concurrent: {
      options: {
        logConcurrentOutput: true
      },
      dev: {
        tasks: ["watch:css", "watch:js"]
      }
    }
  });
  grunt.loadNpmTasks("grunt-scss-lint");
  grunt.loadNpmTasks("grunt-sass");
  grunt.loadNpmTasks("grunt-contrib-watch");
  grunt.loadNpmTasks("grunt-autoprefixer");
  grunt.loadNpmTasks("grunt-jslint");
  grunt.loadNpmTasks("grunt-contrib-uglify");
  grunt.loadNpmTasks("grunt-concurrent");
  grunt.registerTask("default",["concurrent:dev"]);
};
