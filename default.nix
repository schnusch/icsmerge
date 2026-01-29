{ lib
, buildPythonApplication
, aiohttp
, black
, emoji
, flake8
, icalendar
, isort
, mypy
, pythonOlder
, setuptools
, tomli
}:

buildPythonApplication {
  pname = "icsmerge";
  version = "0.0.0";
  pyproject = true;

  disable = pythonOlder "3.8";

  src = ./.;

  build-system = [
    setuptools
  ];

  propagatedBuildInputs = [
    aiohttp
    emoji
    icalendar
  ] ++ lib.optional (pythonOlder "3.11") tomli;

  nativeBuildInputs = [
    black
    flake8
    isort
    mypy
  ];

  pythonImportsCheck = [ "icsmerge" ];

  meta = with lib; {
    license = licenses.gpl2Plus;
    maintainers = with maintainers; [ schnusch ];
  };
}
