desc "Delete created files and directories."
task :clean do
  rm_rf "build"
  rm_rf "dist"
  rm_f "MANIFEST"
end

desc "Run tests."
task :test do
  system "nosetests -v"
end

desc "Run tests on CI server."
task :test_ci do
  system "nosetests -v --with-xunit --xunit-file=results.xml"
end

namespace :pypi do
  desc "Register the package with PyPI"
  task :register => :clean do
    system "python setup.py register"
  end

  desc "Upload a new version to PyPI"
  task :upload => :clean do
    system "python setup.py sdist upload"
    Rake::Task["clean"].reenable
    Rake::Task["clean"].invoke
  end
end

namespace :docs do
  desc "Generate html documentation"
  task :html do
    system "PYTHONPATH='..' make -C docs clean html"
  end
end
