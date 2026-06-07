# Software to draw illustrative figures in papers

Source: Academia Stack Exchange
URL: https://academia.stackexchange.com/questions/1095/software-to-draw-illustrative-figures-in-papers
Tags: writing, software, graphics
Question score: 128 | Views: 154427

## Question

I would like to have suggestions of good software for drawing illustrations in research papers. I already know about Xfig, but this works only on Linux and is at times, clunky when it comes to text. Moreover the resolution is not always perfect making it difficult to manoeuvre the objects. Besides it is tough to learn and master, with all its weird click procedures. 

I would love to know about better alternatives. Not talking about graphs here, just block diagrams and explanatory illustrations.

## Answer 1 (score 90)

A free, fairly portable, and very complete tool for general illustration is Inkscape. It uses SVG as its native file format, and aside from attempting to be a decent drawing tool in its own right, one of its design goals was to provide complete coverage of the features available in SVG.

For block diagrams, flow charts, and other simple sketches of process and data flow there is Dia. It's primary design goal is to duplicate the features of Visio in free software. Like Visio, it uses a stencils and connections drawing model that works really well for diagramming relationships and flow, but gets tedious when attempting to do art.

For clean layout of directed or undirected graph diagrams, it is difficult to beat the Graphviz tools. They are primarily designed to be used from a textual description (a concise intro here (PDF)) of the graph, but there are various GUI tools that can edit their .dot files.

## Answer 2 (score 85) (accepted)

As drawing software, I use OmniGraffle which is much more modern that Xfig, but based on similar principles. It's only available for the Mac and is not free, as far as I know. With little effort, one can produce very attractive diagrams.

I also use Tikz/PGF. It produces very nice diagrams and is very flexible. On the other hand, it requires that you specify the diagram in LaTeX and it has a bit of a steep learning curve.

## Answer 3 (score 40)

I know that TikZ was mentioned already, but I think it deserve its own answer. It is different from Omnigraffle just like TeX is different from Word. But, if you're up for the effort, you'll enjoy the freedom of producing extremely high quality figures!

True, using TikZ for "heavy" diagrams can lead to lengthy compilations, but this can be solved using the externalize library of TikZ, or the Standalone class. See also this possible approach using make.

Although TikZ is not at all WYSIWYG, there are several editors, that enable the use to draw "by hand" the diagram and export it to a Tikz snippet. Personally, I don't have experience with this kind of combination.

Another advantage of TikZ, that as it is somewhat a programing language (after all TeX is turing-complete) you can program your diagram and use external data sources and visualize them. To that end, you can use a combination of TeX, lua or other languages of your choice.

Finally, and most important; TikZ provides an amazing live community which can help you with everything related to it. A perfect starting point would be the TeX.se.

PS: You can also have a look at pstricks. It implements a similar spirit like TikZ but... Well, I'm not using it so I cannot say much. I can say, that I saw amazing outputs of pstricks.

## Answer 4 (score 19)

GeoGebra is free and multi-platform dynamic mathematics software for all levels of education that joins geometry, algebra, tables, graphing, statistics and calculus in one easy-to-use package. Constructions can be made with points, vectors, segments, lines, polygons, conic sections, inequalities, implicit polynomials and functions. All of them can be changed dynamically afterwards. Elements can be entered and modified directly on screen, or through the Input Bar. GeoGebra has the ability to use variables for numbers, vectors and points, find derivatives and integrals of functions and has a full complement of commands like Root or Extremum. Teachers and students can use GeoGebra to make conjectures and prove geometric theorems.

To add something that I personally liked a lot, it has the ability to generate TikZ code for any drawing made using the software! Also, the community recently completed a kick-starter campaign, in which they raised enough funds for an IPad version of the software, to be also available for free! 

[EDIT] - The tablet app is available now, both in App Store and Google Play!
