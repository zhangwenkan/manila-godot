import bpy,json
mat=bpy.data.objects['C25_ContourBuiltCoast'].data.materials[0]
print(json.dumps({'material':mat.name,'nodes':[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None} for n in mat.node_tree.nodes],'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name] for l in mat.node_tree.links]}))
