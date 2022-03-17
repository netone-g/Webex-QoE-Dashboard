$(function(){
    var width = 900;
    var height = 400;
    var svg;
    var graphDatasets ={};
    var mmp = "mmp";
    var cb = "cb";
    var wz = "wz";
    var kinds;
    var nodesData;
    var linksData;
    var link;
    var node;
    var label1;
    var label2;
    var simulation;

    d3.json("resource.json").then(function(data){
        let datasets = data;
        let graphData = [];
        datasets.forEach(function(element, index){
            graphData[index] = element;
        });
        graphDatasets[mmp] = graphData;
        kinks = mmp;
        initDisplay();
        createPanel(mmp); 
        setUpData(kinks,0);
        displayGraph();
    });

    d3.json("resource-wz.json").then(function(data){
        let datasets = data;
        let graphData = [];
        datasets.forEach(function(element, index){
            graphData[index] = element;
        });
        graphDatasets[wz] = graphData;
    });

    d3.json("resource-cb.json").then(function(data){
        let datasets = data;
        let graphData = [];
        datasets.forEach(function(element, index){
            graphData[index] = element;
        });
        graphDatasets[cb] = graphData;
    });
    
    $("#btnmmp").on("click", function(){
        let id = $(this).data("id");
        kinks = mmp;
        initDisplay();
        createPanel(mmp);
        setUpData(kinks, 0);
        displayGraph();
    });

    $("#btnwz").on("click", function(){
        let id = $(this).data("id");
        kinks = wz;
        initDisplay(); 
        createPanel(wz);
        console.log('-----')
        setUpData(kinks, 0);
        displayGraph();
    });

    $("#btncb").on("click", function(){
        let id = $(this).data("id");
        kinks = cb;
        initDisplay(); 
        createPanel(cb);
        setUpData(kinks, 0);
        displayGraph();
    });

    function createPanel(kinds){
        $.each(graphDatasets[kinds], function(index, element){
            $("#te-panel").append(
                "<button type='button' class='btn btn-outline-light te-route' data-id="+index+">Route-"+index+"</button>");
        });
    }
    
    
    $("#te-detail").on("click", function(){
        $("#te-route-information-detail").toggle();
    });
    
    
    $(document).on('click',"button.te-route", function() {
        let id = $(this).data("id");
        $("#topology1").empty();
        nodesData = null;
        linksData = null;
        svg = d3.select("#topology1")
            .append("svg")
            .attr("width", "100%")
            .attr("height", height);
        setUpData(kinks, id);
        displayGraph();
    });
    
    
    function initDisplay(){
        $("#te-panel").empty(); 
        $("#topology1").empty();
        nodesData = null;
        linksData = null; 
        svg = d3.select("#topology1")
            .append("svg")
            .attr("width", "100%")
            .attr("height", height);
    }
    
    function setUpData(kinds, id){
        console.log(graphDatasets);
        console.log(kinks);
        console.log(id);
        nodesData = graphDatasets[kinds][id].nodes;
        linksData = graphDatasets[kinds][id].links;
    }
    
    function displayGraph(){
        link = d3.select("svg")
            .selectAll("line")
            .data(linksData)
            .enter()
            .append("line")
            .attr("stroke-width", 1)
            .attr("stroke", "#FFFFFF");
     
        node = d3.select("svg")
            .selectAll("g")
            .data(nodesData)
            .enter()
            .append("g")
            .attr("class", function(d, i){
                if(i==0){return "te-head"}
                else if(i==nodesData.length-1){return "te-tail"}
                else {return d.nc}
            })
            .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));
    
        svg.selectAll(".active")
            .append("rect")
            .attr("x",0)
            .attr("y",0)
            .attr("rx",20)
            .attr("ry",20)
            .attr("width",40)
            .attr("height",40)
            .attr("fill", "#0096D6");
    
        svg.selectAll(".active")
            .append("rect")
            .attr("x",10)
            .attr("y",10)
            .attr("rx",10)
            .attr("ry",10)
            .attr("width",20)
            .attr("height",20)
            .attr("fill", function(d){
                if(d.rt >= 8){
                    return "#F5A9BC"
                }else{
                    return "#0096D6"
                }
            });
    
        svg.selectAll(".inactive")
            .append("rect")
            .attr("x",0)
            .attr("y",0)
            .attr("rx",20)
            .attr("ry",20)
            .attr("width",40)
            .attr("height",40)
            .attr("fill", "#DCDCDC");
    
        svg.select(".te-head")
            .append('svg:foreignObject')
            .attr("x",2)
            .attr("y",3)
            .attr('height', '40px')
            .attr('width', '40px')
            .attr("fill", "#FFFFFF")
            .html('<i class="fas fa-laptop-house fa-2x"></i>');
        
        svg.select(".te-tail")
            .append('svg:foreignObject')
            .attr("x",2)
            .attr("y",3)
            .attr('height', '40px')
            .attr('width', '40px')
            .attr("fill", "#FFFFFF")
            .html('<i class="fas fa-stop-circle fa-2x"></i>');
    
    
        label1 = d3.select("svg")
            .selectAll("text.label1")
            .data(nodesData)
            .enter()
            .append("text")
            .attr("class", "label1")
            .text(function (d) { 
                return d.name + "(IP:" + d.ip + ")"; })
            .style("text-anchor", "middle")
            .style("fill", function(d){
                if(d.rt >= 8){
                    return "#F5A9A9"
                }else{
                    return "#FFFFFF"
                }
            })
            .style("font-family", "Meiryo")
            .style("font-size", 12);
    
        label2 = d3.select("svg")
            .selectAll("text.label2")
            .data(nodesData)
            .enter()
            .append("text")
            .attr("class", "label2")
            .text(function (d) { 
                return d.lc+"(RT:"+d.rt+")";
            })
            .style("text-anchor", "middle")
            .style("fill", function(d){
                if(d.rt >= 8){
                    return "#F5A9A9"
                }else{
                    return "#FFFFFF"
                }
            })
            .style("font-family", "Meiryo")
            .style("font-size", 12);
    
    
        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().distance(60))
            .force("charge", d3.forceManyBody().strength(-60))
            .force("center", d3.forceCenter(width/2, height/2))
            .force("collision", d3.forceCollide(60));
        
        simulation
            .nodes(nodesData)
            .on("tick", ticked);
     
        simulation.force("link")
            .links(linksData);
    }
    
    function ticked() {
        link
          .attr("x1", function(d) {return d.source.x + 20;})
          .attr("y1", function(d) {return d.source.y + 20;})
          .attr("x2", function(d) {return d.target.x + 20;})
          .attr("y2", function(d) {return d.target.y + 20;});
        node
          .attr("transform", function(d) {return "translate(" + (d.x) + "," + (d.y) + ")";});
        label1
          .attr("x", function(d) {return d.x+10;})
          .attr("y", function(d) {return d.y-10;});
        label2
          .attr("x", function(d) {return d.x+10;})
          .attr("y", function(d) {return d.y-30;});
    }
     
    function dragstarted(d) {
        if(!d3.event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
     
    function dragged(d) {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
    }
     
    function dragended(d) {
        if(!d3.event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    });
    
