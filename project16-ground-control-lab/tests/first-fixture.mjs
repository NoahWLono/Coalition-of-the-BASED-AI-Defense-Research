export const first = {
  id:'interrupted',title:'Interrupted handover',duration:12,checkpoints:[0,3,4,5,7,8,12],
  events:[
    {at:0,type:'owner',actor:'Operator A'},
    {at:0,type:'observe',field:'principal',value:'Link uncertainty'},
    {at:0,type:'observe',field:'mode',value:'Inspection'},
    {at:0,type:'observe',field:'telemetry',value:'Link margin 82 percent'},
    {at:1,type:'alarm',id:'a1',label:'Control link degraded',group:'link',severity:'warning'},
    {at:2,type:'request',id:'h1',from:'Operator A',to:'Operator B',deadline:10},
    {at:3,type:'ack',id:'a1',actor:'Operator B'},
    {at:4,type:'accept',id:'h1',actor:'Operator B'},
    {at:5,type:'interrupt',id:'h1'},
    {at:7,type:'reconcile',actor:'Supervisor',owner:'Operator A'},
    {at:8,type:'clear',id:'a1'},
    {at:8,type:'observe',field:'principal',value:'No active issue'},
    {at:8,type:'complete'}
  ]
};
