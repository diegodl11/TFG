#include<vcg/complex/complex.h>
#include<vcg/complex/algorithms/create/platonic.h>

#include<wrap/io_trimesh/import_ply.h>
#include<wrap/io_trimesh/export_ply.h>
#include<vcg/complex/algorithms/parametrization/voronoi_atlas.h>
#include<vcg/space/outline2_packer.h>

using namespace vcg;
using namespace std;

class MyEdge;
class MyFace;
class MyVertex;
struct MyUsedTypes : public UsedTypes<	Use<MyVertex>   ::AsVertexType,
                                        Use<MyEdge>     ::AsEdgeType,
                                        Use<MyFace>     ::AsFaceType>{};

class MyVertex  : public Vertex<MyUsedTypes, vertex::InfoOcf, vertex::Coord3f, vertex::Normal3f, vertex::TexCoord2f, vertex::VFAdj , vertex::Qualityf, vertex::Color4b, vertex::BitFlags  >{};
class MyFace    : public Face< MyUsedTypes, face::InfoOcf, face::VertexRef, face::CurvatureDirf, face::BitFlags, face::FFAdjOcf ,face::VFAdj , face::WedgeTexCoord2f> {};
class MyEdge    : public Edge< MyUsedTypes>{};
class MyMesh    : public tri::TriMesh< vertex::vector_ocf<MyVertex>, face::vector_ocf<MyFace> , vector<MyEdge>  > {};



int main( int argc, char **argv )
{
  MyMesh startMesh;
  if(argc < 3 )
  {
    printf("Usage: ./normal_filter <input_ply_file> <output_ply_file> [sampleNum] \n");
     return -1;
  }

  //printf("Reading %s and sampling %i \n",argv[1],sampleNum);
  int ret= tri::io::ImporterPLY<MyMesh>::Open(startMesh,argv[1]);
  if(ret!=0)
  {
    printf("Unable to open %s for '%s'\n",argv[1],tri::io::ImporterPLY<MyMesh>::ErrorMsg(ret));
    return -1;
  }

  MyMesh paraMesh;
  tri::VoronoiAtlas<MyMesh>::VoronoiAtlasParam pp;
  pp.sampleNum =(argc > 3) ? atoi(argv[3]) : 10;
  pp.overlap=false;

  tri::VoronoiAtlas<MyMesh>::Build(startMesh,paraMesh,pp);

  tri::io::ExporterPLY<MyMesh>::Save(paraMesh,argv[2],tri::io::Mask::IOM_VERTCOLOR|tri::io::Mask::IOM_WEDGTEXCOORD );
  return 0;
}
