$("#ajax_status_table").ready(function(){
    $.get("ajax_status_table")
});

// window.onload=function(){
//     $.ajax({
//         type:"get",
//         url:"/ajax_status_table",
//         data:{ content },
//         async: false,
//         success:function (data) {
//             for(var i=0;i < data.length;i++){
//                 var x=document.getElementById('ajax_status_table').insertRow();
//                 for(var j=0;j < data[i].length;j++){
//                     var cell=x.insertCell();
//                     cell.innerHTML=data[i][j];
//                 }
//             }
//        }
//     });
// }


function isHumanDetect(){
    if($('#checkbox1').is(':checked')){
        alert("人类检测开启")
        
    }
    else{
        alert("人类检测关闭")
    }
}
function isMoveDetect(){
    if($('#checkbox2').is(':checked')){
        alert("移动检测开启")
    }
    else{
        alert("移动检测关闭")
    }
}
function isSmokeDetect(){
    if($('#checkbox3').is(':checked')){
        alert("烟雾检测开启")
    }
    else{
        alert("烟雾检测关闭")
    }
}
function isFireDetect(){
    if($('#checkbox4').is(':checked')){
        alert("火焰检测开启")
    }
    else{
        alert("火焰检测关闭")
    }
}