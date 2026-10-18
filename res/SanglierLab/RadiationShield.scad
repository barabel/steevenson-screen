include <threads.scad>;

//cup height, depends of polygon in cup module.
cupHeight = 25;
cupSpacing = 16;

//outside and inside diameter of the pipe.
pipe_out = 40;
pipe_in = 33;

//true if rendering the threads.
fullRendering = true;

//polygon( points=[[0,0],[3,0],[21,22],[29,22],[35,15],[35,19],[30,25],[20,25]] )

module cup (){
  rotate_extrude($fn=120) translate([-60, 0, 0]) polygon( points=[[0,0],[2,0],[20.75,23],[29,23],[32.5,19],[35,19],[30,25],[20,25]] );
}

module middle(){
  difference(){
    union(){
      cup();
      for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-cupSpacing]) cylinder(d=10, h=cupSpacing, center=false, $fn=30);
    }
    for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-cupSpacing]) cylinder(d=4.75, h=cupSpacing, center=false, $fn=30);
  }
}

module top(){
   difference(){
      union(){
         cup();
         hull(){
            translate([0, 0, cupHeight-0.1]) cylinder(r=40, h=0.1, center=false, $fn=120);
            translate([0, 0, cupHeight-6]) cylinder(r=44, h=0.1, center=false, $fn=120);
         }
         for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-cupSpacing]) cylinder(d=14, h=cupSpacing-6, center=false, $fn=30);
      }
      for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-cupSpacing+3.5]) cylinder(d=8.5, h=3.25, center=false, $fn=6);
      for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-cupSpacing]) cylinder(d=4.5, h=cupSpacing-6, center=false, $fn=20);      
  }
}
  
module bottom(){
  difference(){
    union(){
      cup();
      for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-5]) cylinder(d=10, h=5, center=false, $fn=30);  
      hull() {
         translate([0, 0, 15-1/2]) cylinder(d=92, h=1, center=true, $fn=120);
         translate([0, 0, 1/2]) cylinder(d=116, h=1, center=true, $fn=120);
       } 
    }
    for(a = [0, 90, 180, 270]) rotate([0, 0, a]) translate([35, 0, cupHeight-5]) cylinder(d=4.5, h=5, center=false, $fn=30);
    metric_thread (diameter=90, pitch=5, angle=45, length=15, internal = true, test = !fullRendering);
  }  
}


module base() {
  difference(){
    union(){
      hull() {
        translate([0, 0, 1/2]) cylinder(d=60, h=1, center=true, $fn=120);
        translate([0, 0, 20-1/2]) cylinder(d=100, h=1, center=true, $fn=120);
      }
      translate([0, 0, 18]) metric_thread (diameter=89, pitch=5, angle=45, length=14, internal = false, test = !fullRendering);
    }
    
    translate([0, 0, 20]) cylinder(d=70, h=15, center=false, $fn=120);  
    
    //cable hole
    cylinder(d=25, h=35, center=false, $fn=120);  
    
    //screws
    for(dx = [-1, 1]) translate([21*dx, 0, 0]){
        cylinder(d=4.5, h=20, center=false, $fn=20);
        translate([0, 0, 20-3]) cylinder(d1=4.5, d2=7, h=3, center=false, $fn=20);
    }
  }
}

module sensorHolder(){
    difference(){
        union(){
           cylinder(d=24.5, h=19, center=false, $fn=60);
           translate([0, 0, 19]) cylinder(d=30, h=3, center=false, $fn=60);
        }
        cylinder(d=6, h=22, center=false, $fn=60);
        cube([0.1, 100, 100], center=true);
    }
}

module finish(stages){    
    
  bottom();    
  
  for(trz=[1:1:(stages-1)]){
    translate([0, 0, trz*cupSpacing]) middle();
  }      
  
  translate([0, 0, stages*cupSpacing]) top();
}

module finishSplitted(stages, tr){   
  translate([0, 0, -3*tr]) base(); 
    
  translate([0, 0, -2*tr]) sensorHolder();
    
  translate([0, 0, 0]) bottom();
    
  
  
  for(trz=[1:1:(stages-1)]){
    translate([0, 0, trz*(25/2 + tr)]) middle();
  }      
  
  translate([0, 0, stages*(25 + tr) ]) top();
}


//finishSplitted(7, 25);  
//finish(7);

//base();
//sensorHolder();
//middle();
bottom();
//cup();
//top();
//polygon( points=[[0,0],[2,0],[20.75,23],[29,23],[32.5,19],[35,19],[30,25],[20,25]] );





