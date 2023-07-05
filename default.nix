{ lib
, buildPythonApplication
, aiohttp
, black
, flake8
, icalendar
, isort
, mypy
, pythonOlder
, tomli
}:

buildPythonApplication {
  pname = "icsmerge";
  version = "0.0.0";

  disable = pythonOlder "3.8";

  src = ./.;

  propagatedBuildInputs = [
    aiohttp
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
