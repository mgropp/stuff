%
% LSV small document class (2013-09-25)
% Author: Martin Gropp
%
% Used fonts (XeTeX required): Quattrocento Sans, Ubuntu,
% Droid Sans Mono
%

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{smalldoc}[2013/09/25 v0.12 small document (LSV)]

\def\BaseClass{scrartcl}

\def\lsv@language{USenglish}
\DeclareOption{de}{\def\lsv@language{german}}
\DeclareOption{de-de}{\def\lsv@language{german}}
\DeclareOption{en}{\def\lsv@language{USenglish}}
\DeclareOption{en-us}{\def\lsv@language{USenglish}}
\DeclareOption{en-uk}{\def\lsv@language{UKenglish}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{\BaseClass}}
%\ExecuteOptions{a4paper}
\ProcessOptions\relax
\LoadClass{\BaseClass}

\RequirePackage{ifxetex}

% amssymb must be included before xunicode
% to avoid \Finv conflict
\RequirePackage{amsmath,amssymb}

\ifxetex
  \RequirePackage{mathspec}
  \RequirePackage{xunicode}
  \defaultfontfeatures{Mapping=tex-text, Numbers={OldStyle,Proportional}}
  \setmainfont{Quattrocento Sans}
  \setromanfont{Quattrocento Sans}
  \setsansfont{Quattrocento Sans}
  \setmonofont[Scale=MatchLowercase]{Droid Sans Mono}
  \setmathfont(Digits,Latin){Quattrocento Sans}
  \newfontfamily\lsvtitlefont{Ubuntu}
\else
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
  \newcommand{\lsvtitlefont}{}
\fi

\RequirePackage[\lsv@language]{babel}
\RequirePackage{graphicx,color,xspace,datetime}
\RequirePackage[usenames]{xcolor}
\RequirePackage[autopunct,german=guillemets,french=guillemets,style=german]{csquotes}
\RequirePackage[automark]{scrpage2}
\RequirePackage{titlesec}
\RequirePackage{enumitem}

\newdateformat{sensibledate}{\THEYEAR-\twodigit{\THEMONTH}-\twodigit{\THEDAY}}

%%% page footer
\pagestyle{scrheadings}
\clearscrheadings
\clearscrplain
\setfootwidth{head}
\ofoot{\pagemark}
\ifoot{\textcolor{black!40}{\footnotesize%
\setbox0=\hbox{\@author}\ifdim\wd0=0pt\else\@author, \fi%
\sensibledate\today, \currenttime}}


%%% titles
\titleformat{\section}%
  {\normalfont\Large\bf\color[gray]{0.4}\lsvtitlefont}%
  {\thesection}%
  {1em}%
  {}%

\titleformat{\subsection}%
  {\normalfont\sffamily\large\color[gray]{0.4}\lsvtitlefont}%
  {\thesubsection}%
  {1em}%
  {}%

\titleformat{\subsubsection}%
  {\normalfont\sffamily\bfseries}%
  {\thesubsubsection}%
  {0.85em}%
  {}%

\titleformat{\paragraph}[runin]%
  {\normalfont\sffamily\bfseries\itshape}%
  {\theparagraph}%
  {0em}%
  {}


%%% paragraphs
\setlength{\parskip}{2ex}


%%% itemize bullets
\ifxetex
  \renewcommand{\labelitemi}{{\raise.3ex\hbox{\scalebox{0.6}{$\bullet$}}}}
\fi


%%% abbreviations
\newcommand{\etc}{\mbox{etc.}\xspace}
\newcommand{\eg}{\mbox{e.\,g.}\xspace}
\newcommand{\ie}{\mbox{i.\,e.}\xspace}
\newcommand{\etal}{\mbox{et al.}\xspace}
\newcommand{\zB}{\mbox{z.\,B.}\xspace}
%\newcommand{\dh}{\mbox{d.\,h.}\xspace}

\endinput
